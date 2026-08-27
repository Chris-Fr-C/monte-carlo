import dataclasses
import duckdb
import functools
import pathlib
from typing import Self
import fintools.interface as i
from loguru import logger


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


@dataclasses.dataclass
class Operator:
    """Database operator for managing quotes data upsert operations.

    Attributes:
        cfg: Configuration instance containing the database connection.
    """
    cfg: Config

    def init(self) -> Self:
        """Initialize the database by executing schema definition language.

        Runs the DDL script to create necessary tables before any operations.

        Returns:
            Self for method chaining.
        """
        res = self.cfg.connection.sql(query=_ddl())
        logger.info("DDL operated. Resulting in {res}", res=res)
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


if __name__ == "__main__":
    """Run the operator with test data for demonstration."""
    import polars as pl

    cfg = Config(duckdb.connect("tmp_db.duckdb"))
    df = pl.read_csv("tmp_test_data.csv")
    with cfg.connection:
        _ = Operator(cfg).init().upsert(df)
