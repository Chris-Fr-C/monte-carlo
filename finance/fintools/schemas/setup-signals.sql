CREATE TABLE IF NOT EXISTS signals (
    ts TIMESTAMP,
    symbol VARCHAR,
    name VARCHAR,
    category VARCHAR,
    confidence FLOAT,
    topology VARCHAR,
    PRIMARY KEY (ts, symbol, name)
);
