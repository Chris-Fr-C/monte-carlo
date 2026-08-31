import vectorbt as vbt
import fintools.core as core
import pendulum

if __name__ == "__main__":
    db = core.Container.db_operator()
    end = pendulum.now()
    start = end - pendulum.Duration(years=4)
    with db:
        data = db.get("NESN.SW", start, end)
        print(data)

    price = data[core.Quotes.close]

    pf = vbt.Portfolio.from_holding(price, init_cash=1000)
    print(price)
    print(pf.total_profit())
