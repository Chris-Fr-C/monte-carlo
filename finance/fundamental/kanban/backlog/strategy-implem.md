# Description
A strategy is a group of N configured signals, and a way to combine them.
Write down the rtrategy trait, and a strategy implemnentation of a strategy called:
`WeightedMajorityStrategy`.
That strategy will evaluate the different signals, get the one that represents at least N% of the signals (for instance >50% of the signals indicate a price that will raise), then average their weight
and returns a buy signal at that moment for backtest evaluation.

# Validation

- Functions are written and tested. Use hardcoded data in the unit test with around 10 different points. Not more.



# Depends on

- strategies-creation.md
# Comments
