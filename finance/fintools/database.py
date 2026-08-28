import dataclasses
import functools
import pathlib
from typing import Self
import polars as pl
import fintools.signals.interface as si

import duckdb
import pendulum
from loguru import logger

import fintools.interface as i


@dataclasses.dataclass
class Config:
    """Configuration for the database connection.

    Attributes:
        connection: DuckDB connection instance used for executing SQL queries.
    """

    connection: duckdb.DuckDBPyConnection = dataclasses.field(
        default_factory=lambda: duckdb.connect("fintools.duckdb")
    )


@functools.lru_cache()
def _signals_ddl() -> str:
    script = pathlib.Path(__file__).parent / "schemas" / "setup-signals.sql"
    with open(script, "r") as fi:
        return fi.read()

@functools.lru_cache()
def _ddl() -> str:
    """Load the database schema definition language from setup.sql.

    Returns:
        The SQL DDL script content from the schemas/setup.sql file.
    """
    script = pathlib.Path(__file__).parent / "schemas" / "setup.sql"
    with open(script, "r") as fi:
        return fi.read()


def _quotes_upsert() -> str:
    """Load the quotes upsert query from quotes-upsert.sql.

    Returns:
        The SQL upsert query content from the schemas/quotes-upsert.sql file.
    """
    script = pathlib.Path(__file__).parent / "schemas" / "quotes-upsert.sql"
    with open(script, "r") as fi:
        return fi.read()

def _signals_upsert() -> str:
    script = pathlib.Path(__file__).parent / "schemas" / "signals-upsert.sql"
    with open(script, "r") as fi:
        return fi.read()


@dataclasses.dataclass
class Operator:
    """Database operator for managing quotes data upsert operations.

    Attributes:
        cfg: Configuration instance containing the database connection.
    """

    cfg: Config
    def __post_init__(self):
        self.init()

    def init(self) -> Self:
        """Initialize the database by executing schema definition language.

        Runs the DDL script to create necessary tables before any operations.

        Returns:
            Self for method chaining.
        """
        res = self.cfg.connection.sql(query=_ddl())
        logger.info("Quotes DDL operated. Resulting in {res}", res=res)

        res = self.cfg.connection.sql(query=_signals_ddl())
        logger.info("Signals DDL operated. Resulting in {res}", res=res)
        return self

    def upsert_signals(self, df: si.SignalDf.DataFrame)->Self:
        query = _signals_upsert()
        _=self.cfg.connection.register("signals_temp_df", df)
        _=self.cfg.connection.execute(query)
        desc=  df.select(pl.col(si.SignalDf.Columns.CATEGORY)).group_by(si.SignalDf.Columns.CATEGORY).count()
        logger.info("Written {n} signals. {desc}", n=len(df), desc=desc)
        _=self.cfg.connection.unregister("signals_temp_df")

        return self

    def upsert(self, df: i.QuotesDf.DataFrame) -> Self:
        """Perform an upsert operation on quotes data using DuckDB.

        Registers the dataframe as a temporary table and executes the upsert SQL query.

        Args:
            df: Polars DataFrame containing quotes data to be upserted.

        Returns:
            Self for method chaining.
        """
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

    def get(
        self, symbol: i.Symbol, start: pendulum.DateTime, end: pendulum.DateTime
    ) -> i.QuotesDf.DataFrame:
        assert start.timezone is not None, "Dates must be timezone aware."
        assert end.timezone is not None, "Dates must be timezone aware."
        return self.cfg.connection.sql(
            """
            SELECT * FROM quotes
            WHERE
                symbol=$1
                AND ts>=$2
                AND ts<=$3
            ORDER BY ts ASC
            """,
            params=(symbol, start, end)
        ).pl(lazy=False) # Not lazy to avoid handling here the connection state.

    def get_all_signals(self)->si.SignalDf.DataFrame:
        return pl.DataFrame(
            self.cfg.connection.sql("select * from signals").to_df(date_as_object=True)
        )

if __name__ == "__main__":
    """Run the operator with test data for demonstration."""
    import polars as pl

    cfg = Config(duckdb.connect("tmp_db.duckdb"))
    df = pl.read_csv("tmp_test_data.csv")
    with cfg.connection:
        _ = Operator(cfg).init().upsert(df)
