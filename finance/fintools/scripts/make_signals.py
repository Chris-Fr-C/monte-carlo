from fintools.scripts.config import YamlConfig
import polars as pl
import click
import yaml
import pendulum
import pathlib
from typing import cast

import fintools.database as database
import fintools.interface as i
import duckdb
import fintools.signals as si

@click.command()
@click.option('--reference', default="./reference.yaml", help='Reference file with the stock symbols and currencies to fetch.')
@click.option('--db', default="./fintools.duckdb", help='Database path')
def main(reference:pathlib.Path, db: pathlib.Path):
    with open(reference, 'r') as fi:
        cfg: YamlConfig= cast(YamlConfig, yaml.safe_load(fi))
    def sanitize(x: str)->str:
        return x.strip().replace(r"\n",x)
    start = pendulum.DateTime.fromisoformat(cfg["start_date"]).in_timezone("Europe/Zurich")


    strategies: list[si.SignalInterface] = [
        si.ema_crossing.EMACrossing(slow_period_days=14,fast_period_days=7)
    ]
    con = duckdb.connect(db)
    with con:
        crud = database.Operator(
            database.Config(
                con
            )
        )
        signals_to_upsert: si.SignalDf.DataFrame = pl.DataFrame()
        for entry in cfg["stocks"]:
            symbol = sanitize(entry["symbol"])
            full_data = crud.get(symbol=symbol, start=start, end=pendulum.now())
            # Computing the signals but historically, for all period.
            for strat in strategies:
                out= strat(full_data, symbol)
                out = out.filter(pl.col(si.SignalDf.Columns.CATEGORY).ne(si.SignalDirection.UNSPECIFIED))
                signals_to_upsert = pl.concat((signals_to_upsert, out), how="vertical" )

        _=crud.upsert_signals(signals_to_upsert)






if __name__ == "__main__":
   main()
