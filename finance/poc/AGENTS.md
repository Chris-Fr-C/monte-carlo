# AGENTS.md

## Project Overview

This project is a quantitative trading and backtesting engine in Python. It fetches OHLCV market data from Yahoo Finance, stores it in an on-disk DuckDB database using Polars, generates technical trading signals, and runs backtests (via `backtesting.py`) considering transaction fees, take-profit, and stop-loss rules.
Project name: fintool
Code will be located under fintool/
Tests will be under tests/

---

## Core Guidelines & Standards

### Package Management & Execution
* Use **`uv`** for all dependency management and environment isolation.
* Run tasks via `uv run pytest`, `uv run python -m ...`, etc. Never use raw `pip` or global `python`.

### Type Hints & Code Style
* **Full imports** use full imports. Never relative imports. Prefer also module import rather than `from a.b.c import x`. Instead prefer `import a.b.c as c`
* **Strict Type Bounding:** 100% type hint coverage on all function signatures, parameters, and return types. Use `typing.Protocol`, `typing.Callable`, `dataclasses`, and standard library generic aliases (`list`, `dict`, `tuple`).
* **No Hardcoded Strings:** Use `enum.Enum` or `enum.StrEnum` for categorical variables (e.g., Signal Directions, Currencies, Order Types, Database Table Names).
* **Docstrings:** Use strict **Google Format Docstrings** for all classes, methods, and functions.
* **Data Processing:** Use **Polars** exclusively for data manipulation and schema management. Avoid `pandas` except where required internally by third-party backtesting visualizers.

### Architecture & Design Patterns
* **Composition over Inheritance:** Avoid deep class hierarchies. Rely on explicit component injection via constructors (`__init__`).
* **Dependency Injection:** Inject external interfaces (such as storage handlers, data fetchers, or signal emitters) through constructors rather than instantiating them internally.
* **Protocols:** Define interface boundaries using `typing.Protocol`.

---

## Architecture Components

### 1. Data Ingestion & Storage (`ingestion/`)
* **Fetcher:** Pulls historical stock quotes (Open, High, Low, Close, Volume, Timestamp with Timezone, Currency) from Yahoo Finance (`yfinance`).
* **Storage:** Stores incoming market quotes into a persistent local DuckDB database (`market_data.duckdb`).
* Data transfer between fetcher, DuckDB, and emitters must use `polars.DataFrame` instances.

### 2. Signal Generation (`signals/`)
* **`SignalEmitter` Protocol:** Interface requiring a `predict(data: pl.DataFrame) -> TradingSignal` method.
* **`TradingSignal` Dataclass:** Captures predicted direction (`SignalDirection` Enum: `UP`, `DOWN`, `NEUTRAL`), confidence level, target timestamp, and metadata.
* **Implementations:**
  * `MovingAverageCrossoverEmitter`: Evaluates fast vs. slow moving average crossovers.
  * `BollingerBandsEmitter`: Evaluates price breakouts relative to upper and lower standard deviation bands.

### 3. Strategy & Backtesting Engine (`backtesting/`)
* Uses `backtesting.py` as the execution engine.
* Combines multiple `SignalEmitter` instances using explicit strategy composition objects.
* Supports configurable fee structures (Percentage-based or Flat per trade).
* Enforces explicit Take Profit (TP) and Stop Loss (SL) parameters on generated orders.
* **Outputs:**
  * Structured performance metric report (Return %, Sharpe Ratio, Max Drawdown, Win Rate, Win/Loss Ratio).
  * Interactive HTML graph detailing equity curves, executed entry/exit orders, and signal occurrences over time.

---

## Project Setup & Workflow Commands

### Initial Setup
uv venv
source .venv/bin/activate
uv add polars duckdb yfinance backtesting pytest matplotlib bokeh

### Run Tests
uv run pytest tests/ -v --cov=.

### Run Ingestion Pipeline
uv run python -m fintools.main fetch --symbol AAPL --interval 1d

### Run Backtest Execution
uv run python -m fintools.main backtest --symbol AAPL --strategy macd_bollinger

---

## Code Structure Blueprint

.
├── AGENTS.md
├── pyproject.toml
├── fintools.
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── enums.py          # Enums for Signals, Currencies, Intervals
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── fetcher.py        # Yahoo Finance fetcher
│   │   └── storage.py        # DuckDB storage engine
│   ├── signals/
│   │   ├── __init__.py
│   │   ├── protocol.py       # SignalEmitter Protocol & Signal dataclass
│   │   ├── ma_crossover.py   # Moving Average implementation
│   │   └── bollinger.py      # Bollinger Bands implementation
│   └── backtest/
│       ├── __init__.py
│       ├── engine.py         # backtesting.py integration wrapper
│       └── metrics.py        # Structured results & export tools
└── tests/
    ├── test_ingestion.py
    ├── test_signals.py
    └── test_backtest.py

---

## Reference Implementation Patterns

### Signal Protocol & Enums Pattern

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Protocol
import polars as pl


class SignalDirection(Enum):
    """Enumeration of possible trading signal directions."""
    UP = auto()
    DOWN = auto()
    NEUTRAL = auto()


class Currency(Enum):
    """Enumeration of supported financial currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


@dataclass(frozen=True)
class TradingSignal:
    """Value object representing a calculated market signal.

    Attributes:
        direction: Predicted market movement direction.
        confidence: Signal strength metric bounded between 0.0 and 1.0.
        timestamp: Time at which the signal was produced.
        symbol: Ticker symbol associated with the signal.
    """
    direction: SignalDirection
    confidence: float
    timestamp: datetime
    symbol: str


class SignalEmitter(Protocol):
    """Protocol defining the interface for all technical signal emitters."""

    def predict(self, data: pl.DataFrame) -> TradingSignal:
        """Evaluates historical price data and outputs a trading signal.

        Args:
            data: Polars DataFrame containing OHLCV market quotes.

        Returns:
            A structured TradingSignal instance.
        """
        ...

### Dependency Injection Pattern

import polars as pl
from typing import Sequence
from fintools.signals.protocol import SignalEmitter, TradingSignal


class CompositeStrategyEvaluator:
    """Evaluates multiple signal emitters via explicit composition.

    Args:
        emitters: Sequence of signal emitters to evaluate.
        weights: Optional list of relative weights for each emitter.
    """

    def __init__(
        self,
        emitters: Sequence[SignalEmitter],
        weights: list[float] | None = None,
    ) -> None:
        self._emitters = list(emitters)
        self._weights = weights or [1.0] * len(emitters)

    def evaluate_all(self, data: pl.DataFrame) -> list[TradingSignal]:
        """Runs price data through all configured signal emitters.

        Args:
            data: Polars DataFrame with required OHLCV columns.

        Returns:
            A list of generated TradingSignal objects.
        """
        return [emitter.predict(data) for emitter in self._emitters]

---

## Testing Requirements

* Write tests using `pytest` fixtures for database connections and mock market data.
* Never make actual external HTTP calls during testing; mock `yfinance` responses using Polars DataFrames.
* Test DuckDB insertions using an in-memory database (`:memory:`) fixture before testing file-based IO.
* Verify edge cases: missing intervals, empty dataframes, single-row dataframes, zero-volatility periods.
