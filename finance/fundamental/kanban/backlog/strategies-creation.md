# Description
Create under src/strategies the trait for a general strategy.

The strategy should at each tick return a structured output.
That output will have something like the following
```
struct StrategySignal {
    timestamp: UtcTimestamp
    position: Buy|Sell|Neutral|Observe;
    strenght: float between 0 and 1.
    composition: SignalOutput[]
}

```

Then create a first strategy where it indicates if the moving average cross and in which direction.


# Validation

- Functions are written and tested. Use hardcoded data in the unit test with around 10 different points. Not more.



# Depends on

- fetch-yahoo-data.md
# Comments
