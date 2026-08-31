CREATE TABLE IF NOT EXISTS quotes (
    ts TIMESTAMP,
    symbol VARCHAR,
    currency VARCHAR,
    close DOUBLE,
    dividends DOUBLE,
    high DOUBLE,
    low DOUBLE,
    open DOUBLE,
    stock_splits DOUBLE,
    volume BIGINT,
    PRIMARY KEY (symbol, ts, currency)
);
