import click
import pendulum
import pandera.typing.polars as pat
import fintools.database as database
import fintools.fetcher as fetcher
import fintools.schemas as s
import fintools.deps as deps

@click.command()
def main():
    cfg = deps.Container.reference()
    con = deps.Container.connection()
    logger = deps.Container.logger()
    logger.info("Writing data into {}", deps.Container.db_path())
    config = fetcher.Config(
        tickers = [fetcher.Stock(symbol=x["symbol"], currency=s.Currency[x["currency"]]) for x in cfg["stocks"]],
        start = pendulum.DateTime.fromisoformat(cfg["start_date"]).in_timezone("Europe/Zurich")
    )
    df = pat.DataFrame[s.Quotes](fetcher.YahooDownloader(config).fetch())
    with con:
        crud = database.Operator(
            database.Config(
                con
            )
        )
        _=crud.upsert(df)



if __name__ == "__main__":
   main()
