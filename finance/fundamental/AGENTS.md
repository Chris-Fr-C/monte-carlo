# Agent Directives & Project Context

## Project Overview
This repository is a **Rust** project. High performance, memory safety, and strict compile-time guarantees are top priorities.
We only use the last versions of library, and of rust.

This project is a trading system that has the following components:
* `src/datamodel`: This module uses Duckdb and ORM to operate on a local database (file).
  It contains a table with the quotes:
  ```d2
    quote: {
        symbol: str (pk)
        ts: Timestamp with timezone (pk)
        currency: str (pk)

        open: float
        high: float
        low: float
        close: float
    }


    signal: {
      process : str (pk)
      symbol: str (pk)
      ts: Timestamp with timezone (pk)
      category: Enum (Up, Down, Volatile, ...)
      duration: int (nb of days)
      intensity: float (0,1) # How strong is the signal. It might be 1 on simple models such as moving average crossing.
    }


    ```

* `src/datasources`: Contains sources to get stock prices. First implementation uses yahoo finance. It is able to load historical data for a specific stock, or get the last quote.
Daily level granularity. It should be able to push into the database from the datamodel module.

& `src/strategies`: Contains strategies. All strategies implement a common trait. That trait allows to return an Option<Signal> when a new stock tick is received.
A signal is a struct that indicates if the stock will:
  - Unspecified
  - Go up
  - Go down
  - Get Volatile
A signal also has a validity period (Duration) and is emitted for a specific date, on a specific symbol.

A strategy has a name, and implement that trait.
An example of strategy would be when two moving averages cross each other (50 days vs 20 days for instance).

Another strategy would be linked to the bollinger bands.

* `src/backtesting`: Contains a strategy backtest. This will use the database data.
This will :
- use the data from the database
- have an initial amount of money defined.
- a list of strategies and their weight
- and a sensibility between 0 and 1 for performing a buy operation. That sensibility applies to the weighed average of the signal intensities.
- a broker fees configuration (% and constant)

This should then test a strategy (weighted combination of strategies) and output a structured report (a struct) with as much information as possible.


## Codebase Conventions & Quality Standards

### Idiomatic Rust Guidelines
* **Safety First:** Avoid using `unsafe` blocks unless explicitly requested or performance-critical. Always document `SAFETY` requirements if `unsafe` is strictly necessary.
* **Error Handling:**
  * Use `thiserror` for library or module-level domain errors.
  * Use `anyhow` for CLI binaries or top-level application entry points (`main.rs`).
  * Prefer `?` error propagation over `.unwrap()` or `.expect()`. Avoid panicking in library code.
* **Concurrency:** Prefer async/await via `tokio` (or standard `std::sync` primitives for synchronous code). Always prefer non-blocking patterns.
* **Clippy:** All code must pass `cargo clippy` without warnings. Treat warnings as errors.
* **Formatting:** Format all code with `rustfmt` before completing a task.

### Project Layout
* `src/main.rs` or `src/lib.rs` — Core entry points.
* `src/bin/` — Supplementary executables.
* `benches/` — Criterion or standard benchmark suites.
* `tests/` — Integration tests. Keep unit tests in the same file as the source code under `#[cfg(test)]`.


---
## Tools
This project will use Taskfile.yml to set up the different launchers.
The Taskfile.yml will be the one having the path to the duck db database file we want to use.

Usage:
`task $command`

It shall include a task to fetch historical data and put them into the database, a task to run backtests etc ...

The schema is found in `https://taskfile.dev/schema.json`

---

## Command Workflows

Before presenting solutions or finalizing code, verify your work using these exact commands:

| Action | Command |
| :--- | :--- |
| **Build Project** | `cargo build` |
| **Run Unit & Integration Tests** | `cargo test` |
| **Format Check** | `cargo fmt --check` |
| **Format Apply** | `cargo fmt` |
| **Run Linter** | `cargo clippy -- -D warnings` |
| **Check Dependencies** | `cargo check` |

---

## Agent Behavior Rules

1. **Incremental Changes:** Propose and make minimal, isolated code edits. Avoid rewriting entire modules when changing a single function.
2. **Keep Tests Green:** Do not break existing unit or integration tests. If a signature changes, update all call sites and test suites accordingly.
3. **No Unnecessary Dependencies:** Do not introduce new crates to `Cargo.toml` without explicit user consent or clear necessity.
4. **Documentation:** Add rustdoc comments (`///`) to all public items (`pub fn`, `pub struct`, `pub enum`).

---

## Common Gotchas & Avoidance
* Do not introduce hidden allocations inside hot loops.
* Be mindful of lifetime constraints when returning references from structs.
* Avoid heavy compute tasks inside async blocks—use `tokio::task::spawn_blocking` if necessary.


# Structure
Use dependency injection when possible to mock external servives in the unit tests. Unit tests should not make any external calls.



# Tracking
Use the `kanban/` folder to understand the tasks to do. You can write under "Comment" section the notes that are important.
When theWhen you work on a ticket, move it from kanban/backlog/  o kanban/progress/
And when it's finished move it from kanban/progress to kanban/uat
