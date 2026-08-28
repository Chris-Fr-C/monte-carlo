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


"""
Take profit stop loss computation:

To break even with a win rate of TP/SL win/risk ratio
we need to win:
SL/(TP+SL)
if TP/SL = 1/2 then we need to win 66% of time.

>>>def f(tp,sl):
...   return sl/(tp+sl)
>>> f(0.04,0.04)
0.5
>>> f(0.04,0.03)
0.4285714285714285
>>> f(0.04,0.06)
0.6
>>>

"""

class CustomStrategy(Strategy):
    all_sigs: si.SignalDf.DataFrame
    symbol: str = ""
    signal_validity: pendulum.Duration = pendulum.Duration(days=1)

    # Risk Management Parameters
    TP: ClassVar[float] = 0.06 # 0.06 but flat fees cause issues with that
    SL: ClassVar[float] = 0.03 # 0.03

    # region lowrisk
    # Strategy Thresholds (CONSERVATIVE SETUP)
    MIN_SCORE_THRESHOLD: ClassVar[float] = 1.80  # Requires multiple confirming signals
    CONSENSUS_RATIO: ClassVar[float] = 0.80      # Requires 80% directional consensus (filters mixed signals)
    SHORT_ALLOWED: ClassVar[bool] = False         # Long-only (avoids fighting long-term equity market drift)

    # Topology Weights (Prioritize structural trends over short-term noise)
    TOPOLOGY_WEIGHTS: ClassVar[dict[str, float]] = {
        "trend": 1.5,        # Primary structural filter
        "momentum": 0.6,     # Secondary momentum confirmation
        "volatility": 0.2,   # Low weight (prevents entry on isolated volatility spikes)
    }
    # endregion lowrisk

    # region normal
    # # Strategy Thresholds
    # MIN_SCORE_THRESHOLD: ClassVar[float] = 0.5  # Adjusted threshold for practical signal matching
    # CONSENSUS_RATIO: ClassVar[float] = 0.60       # Require 60% agreement between bull/bear forces
    # SHORT_ALLOWED: ClassVar[bool] = False
    #
    # # Weight assigned to each topology component
    # TOPOLOGY_WEIGHTS: ClassVar[dict[str, float]] = {
    #     "trend": 1.0,
    #     "momentum": 0.8,
    #     "volatility": 0.5,
    # }
    # endregion normal

    @override
    def init(self):
        con = deps.Container.connection()
        cfg = Config(con)
        with con:
            self.all_sigs = Operator(cfg).get_all_signals()

        self._precompute_signals_and_indicators()
        super().init()

    def _precompute_signals_and_indicators(self):
        """Precomputes weighted score series and chart visual markers via Polars."""
        c = si.SignalDf.Columns

        # 1. Filter signals to current symbol and format timestamps
        sym_sigs = self.all_sigs.filter(pl.col(c.SYMBOL).eq(self.symbol))
        if sym_sigs.is_empty():
            n = len(self.data.index)
            self.bull_scores = np.zeros(n)
            self.bear_scores = np.zeros(n)
            self.buy_counts = np.zeros(n)
            self.sell_counts = np.zeros(n)
            self._setup_ui_indicators()
            return

        # Ensure sym_sigs timestamps are cast cleanly to Datetime
        if sym_sigs[c.TS].dtype == pl.Object:
            sym_sigs = sym_sigs.with_columns(pl.col(c.TS).cast(pl.String).str.to_datetime().alias("sig_ts"))
        elif sym_sigs[c.TS].dtype == pl.String:
            sym_sigs = sym_sigs.with_columns(pl.col(c.TS).str.to_datetime().alias("sig_ts"))
        else:
            sym_sigs = sym_sigs.with_columns(pl.col(c.TS).cast(pl.Datetime).alias("sig_ts"))

        # 2. Extract price dates into a Polars DataFrame with distinct alias
        dates_series = pl.from_pandas(self.data.index.to_series()).cast(pl.Datetime).rename("bar_ts")
        dates_df = pl.DataFrame([dates_series])

        # 3. Join historical signals within the validity window: (bar_ts - validity, bar_ts]
        validity_seconds = self.signal_validity.in_seconds()

        dates_lazy = dates_df.lazy().with_columns(
            (pl.col("bar_ts") - pl.duration(seconds=validity_seconds)).alias("ts_start")
        )

        joined = (
            dates_lazy
            .join_where(
                sym_sigs.lazy(),
                pl.col("sig_ts") >= pl.col("ts_start"),
                pl.col("sig_ts") < pl.col("bar_ts"),
            )
            .collect()
        )

        # 4. Map signals to weighted scores
        if not joined.is_empty():
            directional_scores = joined.with_columns(
                pl.when(pl.col(c.CATEGORY).is_in([
                    si.SignalDirection.UP,
                    si.SignalDirection.MOMENTUM_ACCELERATION,
                    si.SignalDirection.OVERSOLD,
                    si.SignalDirection.BULLISH_DIVERGENCE,
                ]))
                .then(1.0)
                .when(pl.col(c.CATEGORY).is_in([
                    si.SignalDirection.DOWN,
                    si.SignalDirection.MOMENTUM_DECELERATION,
                    si.SignalDirection.OVERBOUGHT,
                    si.SignalDirection.BEARISH_DIVERGENCE,
                ]))
                .then(-1.0)
                .otherwise(0.0)
                .alias("raw_direction"),

                pl.col(c.TOPOLOGY).replace(self.TOPOLOGY_WEIGHTS, default=0.5).alias("topo_weight")
            ).with_columns(
                (pl.col("raw_direction") * pl.col(c.CONFIDENCE) * pl.col("topo_weight")).alias("weighted_score")
            )

            # Aggregate scores per bar_ts
            agg_scores = (
                directional_scores.group_by("bar_ts")
                .agg(
                    pl.col("weighted_score").filter(pl.col("weighted_score") > 0).sum().fill_null(0.0).alias("bull_score"),
                    pl.col("weighted_score").filter(pl.col("weighted_score") < 0).abs().sum().fill_null(0.0).alias("bear_score"),
                    (pl.col(c.CATEGORY).is_in([si.SignalDirection.UP, si.SignalDirection.BULLISH_DIVERGENCE])).sum().alias("buy_count"),
                    (pl.col(c.CATEGORY).is_in([si.SignalDirection.DOWN, si.SignalDirection.BEARISH_DIVERGENCE])).sum().alias("sell_count"),
                )
            )

            final_df = dates_df.join(agg_scores, on="bar_ts", how="left").fill_null(0.0)

            self.bull_scores = final_df["bull_score"].to_numpy()
            self.bear_scores = final_df["bear_score"].to_numpy()
            self.buy_counts = final_df["buy_count"].to_numpy()
            self.sell_counts = final_df["sell_count"].to_numpy()
        else:
            n = len(self.data.index)
            self.bull_scores = np.zeros(n)
            self.bear_scores = np.zeros(n)
            self.buy_counts = np.zeros(n)
            self.sell_counts = np.zeros(n)

        self._setup_ui_indicators()

    def _setup_ui_indicators(self):
        """Helper to register indicators for visual overlay in backtesting UI."""
        def scatter_points(counts_series: np.ndarray, price_series: np.ndarray) -> np.ndarray:
            return np.where(counts_series > 0, price_series, np.nan)

        self.I(lambda: self.bull_scores, name="Bull Intensity Score", color="green")
        self.I(lambda: self.bear_scores, name="Bear Intensity Score", color="red")

        self.I(
            scatter_points,
            self.buy_counts,
            self.data.Low * 0.99,
            name="Buy Marker",
            overlay=True,
            scatter=True,
            color="green",
        )
        self.I(
            scatter_points,
            self.sell_counts,
            self.data.High * 1.01,
            name="Sell Marker",
            overlay=True,
            scatter=True,
            color="red",
        )

    def evaluate_signals(self, idx: int) -> si.SignalDirection:
        """Evaluates weighted multi-topology decision for a specific step index."""
        bull_score = self.bull_scores[idx]
        bear_score = self.bear_scores[idx]
        total_score = bull_score + bear_score

        if total_score == 0:
            return si.SignalDirection.UNSPECIFIED

        bull_ratio = bull_score / total_score
        bear_ratio = bear_score / total_score

        if bull_score >= self.MIN_SCORE_THRESHOLD and bull_ratio >= self.CONSENSUS_RATIO:
            return si.SignalDirection.UP
        elif bear_score >= self.MIN_SCORE_THRESHOLD and bear_ratio >= self.CONSENSUS_RATIO:
            return si.SignalDirection.DOWN

        return si.SignalDirection.UNSPECIFIED

    @override
    def next(self):
        if self.position:
            return

        idx = len(self.data) - 1
        decision = self.evaluate_signals(idx)
        cl = self.data.Close[-1]

        # Calculate dynamic position size risking 2% of portfolio equity per trade
        # risk_per_trade = self.equity * 0.9# 0.02
        # stop_distance = cl * self.SL
        # size = int(risk_per_trade / stop_distance)
        # size = 0.95

        if decision == si.SignalDirection.UP:
            tp = cl * (1 + self.TP)
            sl = cl * (1 - self.SL)
            self.buy( sl=sl, tp=tp)
            logger.info("BUY order placed at {} for price {}", self.data.index[-1], cl)

        elif decision == si.SignalDirection.DOWN and self.SHORT_ALLOWED:
            tp = cl * (1 - self.TP)
            sl = cl * (1 + self.SL)
            self.sell(sl=sl, tp=tp)
            logger.info("SELL order placed at {} for price {}", self.data.index[-1], cl)

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
                cash=1000,
                commission=fees,  # 0.002), # swiss quotes seem to have flat commission: https://www.swissquote.com/en-ch/private/trade/pricing/securities/stocks
                exclusive_orders=True,
            )
            logger.info("Treating {}", symbol)
            output = bt.run(symbol=symbol)
            output["symbol"]=symbol
            reports.append(output.rename(symbol))
            bt.plot(filename=f"./data/tmp_backtest_{symbol}", open_browser=False)

        out = pd.concat(reports, axis=1)
        out.to_csv("./data/tmp_report.csv")
        out.transpose().to_csv("./data/tmp_report_transposed.csv")
        print(out)
