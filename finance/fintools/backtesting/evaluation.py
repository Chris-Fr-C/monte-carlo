from typing import ClassVar, override
import numpy as np

import pandas as pd
import pendulum
import polars as pl
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA

import fintools.deps as deps
import fintools.interface as i
import fintools.signals.interface as si
from fintools.database import Config, Operator

logger = deps.Container.logger()


class CustomStrategy(Strategy):
    all_sigs: si.SignalDf.DataFrame
    symbol: str = ""
    signal_validity: pendulum.Duration = pendulum.Duration(days=1)
    TP: ClassVar[float] = 0.02
    SL: ClassVar[float] = 0.04

    @override
    def init(self):
        # for perf we fetch once then we filter
        con = deps.Container.connection()
        cfg = Config(con)
        with con:
            self.all_sigs = Operator(cfg).get_all_signals()



        self._precompute_signals_for_ui()
        super().init()

    def _precompute_signals_for_ui(self):
        # this function is shit, gotta rewrite it
        def signal_points(
            counts_series: np.ndarray, price_series: np.ndarray
        ) -> np.ndarray:
            """Returns price points where signal counts > 0, and NaN elsewhere."""
            return np.where(counts_series > 0, price_series, np.nan)

        c = si.SignalDf.Columns
        timestamps = self.data.index

        buy_counts = []
        sell_counts = []

        for ts in timestamps:
            sigs = self._find_signal(ts)
            if sigs.is_empty():
                buy_counts.append(0)
                sell_counts.append(0)
            else:
                counts = dict(sigs["category"].value_counts().iter_rows())
                buy_counts.append(counts.get("up", 0))
                sell_counts.append(counts.get("down", 0))

        # Store counts arrays for decision logic in next()
        self.buy_counts = np.array(buy_counts)
        self.sell_counts = np.array(sell_counts)

        # 3. Declare indicators using self.I for plotting
        # Panel 1: Number of signal events in a separate subplot panel below price
        self.I(lambda: self.buy_counts, name="Buy Signal Count", color="green")
        self.I(lambda: self.sell_counts, name="Sell Signal Count", color="red")

        # Panel 2: Visual scatter markers overlaid on the Price chart
        self.I(
            signal_points,
            self.buy_counts,
            self.data.Low * 0.99,  # Placed slightly below low price
            name="Buy Signal Marker",
            overlay=True,
            scatter=True,
            color="green",
        )
        self.I(
            signal_points,
            self.sell_counts,
            self.data.High * 1.01,  # Placed slightly above high price
            name="Sell Signal Marker",
            overlay=True,
            scatter=True,
            color="red",
        )

    def weight_decision(self, df: si.SignalDf.DataFrame) -> si.SignalDirection:
        c = si.SignalDf.Columns
        # step 1: we check if we have a clear majority on what to do.
        momentum = df.filter(pl.col(c.TOPOLOGY)=="momentum")
        trend = df.filter(pl.col(c.TOPOLOGY)=="trend")
        volatility = df.filter(pl.col(c.TOPOLOGY)=="volatility")
        counts: dict[str, int] = dict(df["category"].value_counts().iter_rows())
        up = counts.get("up", 0)
        down = counts.get("down", 0)
        if down == 0:
            up_down_ratio = 1
        else:
            up_down_ratio = up / down

        if up == 0:
            down_up_ratio = 1
        else:
            down_up_ratio = down / up

        sensibility = 0.9
        min_votes = 3
        if up_down_ratio > sensibility and up>min_votes:
            return si.SignalDirection.UP
        elif down_up_ratio > sensibility and down>min_votes:
            return si.SignalDirection.DOWN
        else:
            return si.SignalDirection.UNSPECIFIED

    @override
    def next(self):
        assert self.symbol
        ts = self.data.index[-1]
        sigs = self._find_signal(ts)
        if sigs.is_empty():
            return
        dec = self.weight_decision(sigs)

        c = si.SignalDf.Columns
        buy_sigs = (
            sigs.filter(pl.col(c.CATEGORY).eq("up"))
            .with_columns(pl.lit(1).alias("buy_signal"))
            .to_pandas()
            .set_index(c.TS)
        )
        sell_sigs = (
            sigs.filter(pl.col(c.CATEGORY).eq("down"))
            .with_columns(pl.lit(1).alias("sell_signal"))
            .to_pandas()
            .set_index(c.TS)
        )

        # HERE i want to put the amount of buy sell events in graph

        cl = self.data.Close[-1]
        tp = cl * (1 + self.TP)
        sl = cl * (1 - self.SL)

        # if sigs["category"][0]=="up":
        if dec == si.SignalDirection.UP:
            _ = self.buy(sl=sl, tp=tp)
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

def fees(order_size: int, price: float) -> float:
    """https://www.swissquote.com/en-ch/private/trade/pricing/securities/stocks"""
    if order_size <= 500:
        return 3
    elif order_size <= 1000:
        return 5
    elif order_size <= 2000:
        return 10
    elif order_size <= 10000:
        return 29
    elif order_size <= 15000:
        return 40
    elif order_size <= 25_000:
        return 79
    else:
        raise Exception("Didnt code that cause i dont have thaaat amount of money")


if __name__ == "__main__":
    symbol = "NESN.SW"
    logger.error(deps.Container.db_path())
    con = deps.Container.connection()
    start = pendulum.now() - pendulum.Duration(months=24)
    end = pendulum.now()
    with con:
        cfg = Config(connection=con)

        symbs = [
            x["symbol"]
            for x in deps.Container.reference()["stocks"]
            if x["currency"] == "CHF"
        ]
        # Availability
        reports: list[pd.Series] = []
        for symbol in symbs:

            data = Operator(cfg).get(symbol, start=start, end=end)
            data = data.drop_nulls()
            backtest_data = _rename_for_backtest(data)
            if backtest_data.empty:
                logger.warning("Skipping empty {}", symbol)
                continue

            bt = Backtest(
                backtest_data,
                CustomStrategy,
                cash=10000,
                commission=fees,  # 0.002), # swiss quotes seem to have flat commission: https://www.swissquote.com/en-ch/private/trade/pricing/securities/stocks
                exclusive_orders=True,
            )
            logger.info("Treating {}", symbol)
            output = bt.run(symbol=symbol)
            output["symbol"]=symbol
            reports.append(output.rename(symbol))
            bt.plot(filename=f"./data/tmp_backtest_{symbol}")

    out = pd.concat(reports, axis=1)
    out.to_csv("./data/tmp_report.csv")
    print(out)
