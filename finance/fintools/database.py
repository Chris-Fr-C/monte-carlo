import dataclasses
import duckdb
import functools
import pathlib
from typing import Self
import fintools.interface as i
from loguru import logger


@dataclasses.dataclass
class Config:
    connection: duckdb.DuckDBPyConnection = dataclasses.field(
        default_factory=lambda: duckdb.connect("fintools.duckdb")
    )


@functools.lru_cache()
def _ddl() -> str:
    script = pathlib.Path(__file__).parent / "schemas" / "setup.sql"
    with open(script, "r") as fi:
        return fi.read()


def _quotes_upsert() -> str:
    script = pathlib.Path(__file__).parent / "schemas" / "quotes-upsert.sql"
    with open(script, "r") as fi:
        return fi.read()


@dataclasses.dataclass
class Operator:
    cfg: Config

    def init(self) -> Self:
        res = self.cfg.connection.sql(query=_ddl())
        logger.info("DDL operated. Resulting in {res}", res=res)
        return self

    def upsert(self, df: i.QuotesDf.DataFrame) -> Self:
        query = _quotes_upsert()
        _ = self.cfg.connection.register("quotes_temp_df", df)
        res = self.cfg.connection.execute(query=query)
        logger.info(
            "Upsert operation performed on {n} rows and resulting in {res}",
            n=len(df),
            res=res,
        )
        # No need to try except cause we want to have it present to debug.
        _ = self.cfg.connection.unregister("temp_df")

        return self


if __name__ == "__main__":
    import polars as pl

    cfg = Config(duckdb.connect("tmp_db.duckdb"))
    df = pl.read_csv("tmp_test_data.csv")
    with cfg.connection:
        Operator(cfg).init().upsert(df)
