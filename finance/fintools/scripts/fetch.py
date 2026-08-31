import click
import pendulum
import pandera.typing.polars as pat
import fintools.core as c
import fintools.fetcher as fetcher

@click.command()
def main():
    cfg = c.Container.reference()
    con = c.Container.connection()
    logger = c.Container.logger()
    logger.info("Writing data into {}", c.Container.db_path())
    config = fetcher.Config(
        tickers = [fetcher.Stock(symbol=x["symbol"], currency=c.Currency[x["currency"]]) for x in cfg["stocks"]],
        start = pendulum.DateTime.fromisoformat(cfg["start_date"]).in_timezone("Europe/Zurich")
    )
    df = pat.DataFrame[c.Quotes](fetcher.YahooDownloader(config).fetch())
    with con:
        crud = c.DbOperator(
            c.DbConfig(
                con
            )
        )
        _=crud.upsert(df)



if __name__ == "__main__":
   main()
