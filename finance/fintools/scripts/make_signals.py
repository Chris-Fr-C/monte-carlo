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
        # trends
        si.trend.ADXSignal(),
        si.trend.AroonSignal(),
        si.trend.CCISignal(),
        si.trend.DPOSignal(),
        si.trend.EMASignal(),
        si.trend.IchimokuSignal(),
        si.trend.KSTSignal(),
        si.trend.MACDSignal(),
        si.trend.MassIndexSignal(),
        si.trend.PSARSignal(),
        si.trend.STCSignal(),
        si.trend.TRIXSignal(),
        si.trend.VortexSignal(),
        si.trend.WMASignal(),

        # momentum
        si.momentum.AwesomeOscillatorSignal(),
        si.momentum.KAMASignal(),
        si.momentum.PPOSignal(),
        si.momentum.PVOSignal(),
        si.momentum.ROCSignal(),
        si.momentum.StochRSISignal(),
        si.momentum.StochasticOscillatorSignal(),
        si.momentum.TSISignal(),
        si.momentum.UltimateOscillatorSignal(),
        si.momentum.WilliamsRSignal(),


        # volatility
        si.volatility.AverageTrueRange(),
        si.volatility.BollingerBandsCrossing(),
        si.volatility.DonchianChannelCrossing(),
        si.volatility.KeltnerChannelCrossing(),
        si.volatility.UlcerIndexCrossing(),
     ]
    # first we just take the default for everything we have


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
