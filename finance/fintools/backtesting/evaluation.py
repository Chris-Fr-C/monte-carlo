import pendulum

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import polars as pl
from backtesting.test import SMA, GOOG
import pandas as pd
from fintools.database import Operator, Config
import fintools.interface as i
import fintools.deps as deps
import fintools.signals.interface as si

logger = deps.Container.logger()


class CustomStrategy(Strategy):
    all_sigs: si.SignalDf.DataFrame
    symbol: str = ""
    signal_validity: pendulum.Duration = pendulum.Duration(days=1)
    TP=0.02
    SL=0.04

    def init(self):
        # for perf we fetch once then we filter
        con = deps.Container.connection()
        cfg = Config(con)
        with con:
            self.all_sigs = Operator(cfg).get_all_signals()
        super().init()

    def next(self):
        assert self.symbol
        ts = self.data.index[-1]
        sigs = self._find_signal(ts)
        if sigs.is_empty():
            return
        # TODO: aggregate if we have multiple
        sigs = sigs.head(n=1)
        cl = self.data.Close[-1]
        tp = cl*(1+self.TP)
        sl = cl*(1-self.SL)
        if sigs["category"][0]=="up":
            self.buy(
                size=1,
                sl = sl, tp=tp)
            logger.info("order placed at {} for {}", ts, cl)

    def _find_signal(self, ts: pendulum.DateTime) -> si.SignalDf.DataFrame:
        c = si.SignalDf.Columns
        return self.all_sigs.filter(
            pl.col(c.SYMBOL).eq(self.symbol)
            & pl.col(c.TS).le(ts)
            & pl.col(c.TS).gt(ts - self.signal_validity)
        )


class SmaCross(Strategy):
    n1 = 10
    n2 = 20

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.position.close()
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.position.close()
            self.sell()


def _rename_for_backtest(df: i.QuotesDf.DataFrame) -> pd.DataFrame:
    def rename_col(x: str) -> str:
        return x.capitalize()

    c = i.QuotesDf.Columns
    df = df.select(
        pl.col(c.TS),
        pl.col(c.OPEN).alias("Open"),
        pl.col(c.HIGH).alias("High"),
        pl.col(c.LOW).alias("Low"),
        pl.col(c.CLOSE).alias("Close"),
        pl.col(c.VOLUME).alias("Volume"),
    )
    return df.to_pandas().set_index("ts")


if __name__ == "__main__":
    symbol = "NESN.SW"
    logger.error(deps.Container.db_path())
    con = deps.Container.connection()
    start = pendulum.now() - pendulum.Duration(months=24)
    end = pendulum.now()
    with con:
        cfg = Config(connection=con)
        data = Operator(cfg).get(symbol, start=start, end=end)
        data = data.drop_nulls()
        backtest_data = _rename_for_backtest(data)
    bt = Backtest(
        backtest_data,
        CustomStrategy,
        cash=1000,
        commission=(7, 0.002), # swiss quotes seem to have flat commission: https://www.swissquote.com/en-ch/private/trade/pricing/securities/stocks
        exclusive_orders=True,
    )

    output = bt.run(symbol=symbol)
    bt.plot()
