# Kanban board

## Backlog

* [Task-001] Create data model

> summary: Create the datamodel (quote, signal ...) as described in the AGENTS.md.
> validation: Data model is created and available under src/datamodel and tests are written and passing.
> priority: low

* [Task-002] Create Duck DB Operations
> summary: Create under datamodel/operations.rs the different CRUD operations for each of the model table.
We should be able to upsert quotes, signals etc ...
> validation: Functions are written and tested.
> priority: low
> dependencies: Task-001

* [Task-003] Fetch yahoo finance data
> summary: Create under src/datasources an object/function to fetch data from yahoo for a specific symbol,
> validation:
>> Functions are written and tested. Use mocks instead of performing a real api call.
>> One Taskfile task should allow to fetch the data for a specific symbol and insert it into the duckdb database file.
> dependencies: Task-002
> priority: low

* [Task-004] Strategy creation
> summary: A strategy is a group of N configured signals, and a way to combine them.
    Write down the strategy trait, and a strategy implemnentation of a strategy called:
    `WeightedMajorityStrategy`.
    That strategy will evaluate the different signals, get the one that represents at least N% of the signals (for instance >50% of the signals indicate a price that will raise), then average their weight
    and returns a buy signal at that moment for backtest evaluation.
    The output of the strategy evaluation would look like something like this:
    ```rust
    // This is pseudo code
    struct StrategyEvaluation {
        timestamp: UtcTimestamp
        position: Buy|Sell|Neutral|Observe;
        strenght: float between 0 and 1.
        composition: SignalOutput[]
    }
    ```
> validation: functions are written and tested. Use hardcoded data in the unit test with around 10 different points. Not more.
> dependencies: Task-003

* [Task-005]: Create backtesting
> summary: Create under src/backtesting the required functions to evaluate the impact of each signal into the quote (stock price).
It should generate:
>> A structured output (struct) per signal.
>> A structured output (struct) for the strategy.
> It should be configurable with an input struct that would have
>the fee cost (flat or %), initial money,  etc ...
>
> validation: Functions are written and tested. Use hardcoded data in the unit test with around 10 different points. Not more.
> dependencies: Task-004







--

## Ongoing

## Uat


## Finished
