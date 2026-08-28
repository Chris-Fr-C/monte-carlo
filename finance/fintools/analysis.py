import duckdb
import ta
import fintools.interface as i
import fintools.database as database
from collections.abc import Iterable
import pendulum
from typing import cast
import polars as pl
import dataclasses

@dataclasses.dataclass()
class TAEnriched():
    df: i.EnrichedQuotesDf.DataFrame

@dataclasses.dataclass()
class RawData():
    raw: i.QuotesDf.DataFrame

    def enrich(self)->TAEnriched:
        c = i.QuotesDf.Columns

        # First we need to split the normalized df into smaller df to be ta compatible
        symbols: Iterable[str] = cast(Iterable[str],self.raw[c.SYMBOL].unique())
        groups: list[pl.DataFrame] = []
        for symbol in symbols:
            sub = self.raw.filter(pl.col(c.SYMBOL).eq(symbol))
            annoying_pandas = ta.add_all_ta_features(
                sub.to_pandas(),
                    open=c.OPEN,
                    high=c.HIGH,
                    low=c.LOW,
                    close=c.CLOSE,
                    volume=c.VOLUME,
                    fillna=True,
                )
            groups.append(pl.from_pandas(annoying_pandas))
        out = pl.concat(groups, how="vertical")
        return TAEnriched(out)





if __name__ == "__main__":
    end = pendulum.now(tz="Europe/Zurich")
    start = end - pendulum.Duration(months=6)
    con = duckdb.connect("tmp_db.duckdb")
    db = database.Operator(database.Config(connection=con))
    with con:
        df = db.get("NESN.SW", start, end)

        enriched = RawData(df).enrich()
        print(enriched.df)
        # For debugging and analysis.
        con.register("quotes_enriched", enriched.df)
