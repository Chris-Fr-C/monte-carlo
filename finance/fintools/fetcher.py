from dataclasses import dataclass, field
from typing import NamedTuple
import pendulum

import fintools.interface as c
import polars as pl
import pandas as pd
import yfinance
import requests


class Stock(NamedTuple):
    symbol: c.Symbol
    currency: c.Currency


@dataclass
class Config:
    tickers: list[Stock]
    session: requests.Session = field(default_factory=requests.Session)
    start: pendulum.DateTime = field(
        default_factory=lambda: (
            pendulum.now("Europe/Zurich") - pendulum.Duration(months=12)
        )
    )
    end: pendulum.DateTime = field(
        default_factory=lambda: pendulum.now("Europe/Zurich")
    )


@dataclass
class YahooDownloader:
    cfg: Config

    def _tickers(self) -> yfinance.Tickers:
        return yfinance.Tickers(
            [x.symbol for x in self.cfg.tickers],
            session=self.cfg.session,
        )

    def fetch(self) -> pl.DataFrame:
        data: pd.DataFrame | None = self._tickers().download(
            start=self.cfg.start, end=self.cfg.end
        )
        assert data is not None
        assert not data.empty
        # that data has a multi index which is annoying. I prefer to normalize that instead.
        df_flat = data.stack(level=1, future_stack=True).reset_index()
        symbol_currencies: dict[c.Symbol, c.Currency] = {
            x.symbol: x.currency for x in self.cfg.tickers
        }
        pl_df = pl.from_pandas(df_flat).rename(
            {
                "Ticker": c.QuotesDf.Columns.SYMBOL,
                "Open": c.QuotesDf.Columns.OPEN,
                "High": c.QuotesDf.Columns.HIGH,
                "Low": c.QuotesDf.Columns.LOW,
                "Close": c.QuotesDf.Columns.CLOSE,
                "Volume": c.QuotesDf.Columns.VOLUME,
                "Dividends": c.QuotesDf.Columns.DIVIDENDS,
                "Stock Splits": c.QuotesDf.Columns.STOCK_SPLITS,
                "Date": c.QuotesDf.Columns.TS,
            }
        )
        pl_df = pl_df.with_columns(
            pl.col(c.QuotesDf.Columns.SYMBOL).replace(symbol_currencies).alias(c.QuotesDf.Columns.CURRENCY)
        )

        return pl_df


if __name__ == "__main__":
    d = YahooDownloader(Config([Stock("NESN.SW", c.Currency.CHF)])).fetch()
    d.write_csv("tmp_test_data.csv")
    print(d)
