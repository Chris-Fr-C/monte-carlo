import pathlib
from typing import Literal, TypedDict, cast

import click
import duckdb
import pandas as pd
import pendulum
import yaml

import fintools.database as database
import fintools.fetcher as fetcher
import fintools.interface as i


class _YamlSymbolConfig(TypedDict):
    symbol: str
    currency: Literal["CHF", "USD", "EUR"]

class YamlConfig(TypedDict):
    stocks: list[_YamlSymbolConfig]
    start_date: str

@click.command()
@click.option('--reference', default="./reference.yaml", help='Reference file with the stock symbols and currencies to fetch.')
@click.option('--db', default="./fintools.duckdb", help='Database path')
def main(reference:pathlib.Path, db: pathlib.Path):
    with open(reference, 'r') as fi:
        cfg: YamlConfig= cast(YamlConfig, yaml.safe_load(fi))

    config = fetcher.Config(
        [
            fetcher.Stock(
                symbol=x["symbol"], currency=i.Currency[x["currency"]]
            ) for x in cfg["stocks"]
        ],
        start = pendulum.DateTime.fromisoformat(cfg["start_date"]).in_timezone("Europe/Zurich")
    )
    df = fetcher.YahooDownloader(config).fetch()
    con = duckdb.connect(db)
    with con:
        crud = database.Operator(
            database.Config(
                con
            )
        )
        _=crud.upsert(df)



if __name__ == "__main__":
   main()
