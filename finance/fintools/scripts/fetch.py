import click
import pendulum

import fintools.database as database
import fintools.fetcher as fetcher
import fintools.interface as i
import fintools.deps as deps

@click.command()
def main():

    cfg = deps.Container.reference()
    con = deps.Container.connection()
    config = fetcher.Config(
        tickers = [fetcher.Stock(symbol=x["symbol"], currency=i.Currency[x["currency"]]) for x in cfg["stocks"]],
        start = pendulum.DateTime.fromisoformat(cfg["start_date"]).in_timezone("Europe/Zurich")
    )
    df = fetcher.YahooDownloader(config).fetch()
    with con:
        crud = database.Operator(
            database.Config(
                con
            )
        )
        _=crud.upsert(df)



if __name__ == "__main__":
   main()
