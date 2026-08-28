import duckdb

import ta
import fintools.interface as i
import fintools.database as database
import pendulum
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
        annoying_pandas = ta.add_all_ta_features(
            self.raw.to_pandas(),
                open=c.OPEN,
                high=c.HIGH,
                low=c.LOW,
                close=c.CLOSE,
                volume=c.VOLUME,
                fillna=True,
            )
        df = pl.from_pandas(annoying_pandas)

        return TAEnriched(df)





if __name__ == "__main__":
    end = pendulum.now(tz="Europe/Zurich")
    start = end - pendulum.Duration(months=6)
    con = duckdb.connect("tmp_db.duckdb")
    db = database.Operator(database.Config(connection=con))
    with con:
        df = db.get("NESN.SW", start, end)
    print(RawData(df).enrich().df)
