from fintools.config import YamlConfig
import polars as pl
import click
import yaml
import pendulum
import pathlib
from typing import Counter, cast

import fintools.database as database
import fintools.interface as i
import duckdb
import fintools.signals as si
import fintools.deps as deps

@click.command()
def main():
    reference = deps.Container.reference()
    con=deps.Container.connection()
    start = pendulum.DateTime.fromisoformat(reference["start_date"]).in_timezone("Europe/Zurich")


    logger = deps.Container.logger()
    strategies: list[si.SignalInterface] = [
        si.ema_crossing.EMACrossing(slow_period_days=14,fast_period_days=7),
        si.momentum.KAMACrossing(),
        si.momentum.AwesomeOscillatorCrossing(),
    ]
    with con:
        crud = database.Operator(
            database.Config(
                con
            )
        )
        signals_to_upsert: si.SignalDf.DataFrame = pl.DataFrame()
        counter: Counter[str]= Counter()
        for entry in reference["stocks"]:
            symbol = entry["symbol"]
            full_data = crud.get(symbol=symbol, start=start, end=pendulum.now())
            # Computing the signals but historically, for all period.
            for strat in strategies:
                out= strat(full_data, symbol)
                out = out.filter(pl.col(si.SignalDf.Columns.CATEGORY).ne(si.SignalDirection.UNSPECIFIED))
                signals_to_upsert = pl.concat((signals_to_upsert, out), how="vertical" )
                counter[strat.name()]+=len(out)
        logger.info("{} signals generated.", counter)

        _=crud.upsert_signals(signals_to_upsert)






if __name__ == "__main__":
   main()
