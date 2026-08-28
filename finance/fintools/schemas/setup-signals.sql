CREATE TABLE IF NOT EXISTS signals (
    ts TIMESTAMP,
    symbol VARCHAR,
    name VARCHAR,
    category VARCHAR,
    confidence FLOAT,
    PRIMARY KEY (ts, symbol, name)
);
