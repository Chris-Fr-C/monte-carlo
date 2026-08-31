"""Module for fetching stock quotes from Yahoo Finance.

This module provides functionality to download historical price data for
stock tickers using the Yahoo Finance API via the `yfinance` library.
"""

from dataclasses import dataclass, field
from typing import NamedTuple
import pendulum


import fintools.core as s
import polars as pl
import pandas as pd
import yfinance
import requests


class Stock(NamedTuple):
    """Stock identifier combining a ticker symbol and its currency.

    Args:
        symbol: The stock ticker symbol (e.g., "NESN.SW").
        currency: The currency code for the stock's price quotes.

    Example:
        >>> Stock("NESN.SW", c.Currency.CHF)
        Stock(symbol='NESN.SW', currency=Currency.CHF)
    """

    symbol: s.Symbol
    currency: s.Currency



@dataclass
class Config:
    """Configuration for stock data fetching.

    Args:
        tickers: List of stocks to fetch price data for.
        session: HTTP session used for making requests to Yahoo Finance.
        start: The start date for the historical data range (inclusive).
            Defaults to 12 months ago from the current time in Zurich timezone.
        end: The end date for the historical data range (inclusive).
            Defaults to today's date in Zurich timezone.

    Example:
        >>> cfg = Config(tickers=[Stock("NESN.SW", c.Currency.CHF)])
    """

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
    """Downloads stock quotes from Yahoo Finance.

    Args:
        cfg: Configuration object specifying tickers and other fetch settings.
    """

    cfg: Config

    def _tickers(self) -> yfinance.Tickers:
        return yfinance.Tickers(
            tickers=[x.symbol for x in self.cfg.tickers],
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
        symbol_currencies: dict[s.Symbol, s.Currency] = {
            x.symbol: x.currency for x in self.cfg.tickers
        }
        pl_df = pl.from_pandas(df_flat).rename(
            {
                "Ticker": s.Quotes.symbol,
                "Open": s.Quotes.open,
                "High": s.Quotes.high,
                "Low": s.Quotes.low,
                "Close": s.Quotes.close,
                "Volume": s.Quotes.volume,
                "Dividends": s.Quotes.dividends,
                "Stock Splits": s.Quotes.stock_splits,
                "Date": s.Quotes.ts,
            }
        )
        pl_df = pl_df.with_columns(
            pl.col(s.Quotes.symbol).replace(symbol_currencies).alias(s.Quotes.currency)
        )

        return pl_df


if __name__ == "__main__":
    d = YahooDownloader(Config([Stock("NESN.SW", s.Currency.CHF)])).fetch()
    d.write_csv("tmp_test_data.csv")
    print(d)
