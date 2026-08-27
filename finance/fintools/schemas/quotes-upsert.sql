INSERT INTO quotes
    SELECT
        ts, symbol, currency, close, dividends, high, low, open, stock_splits, volume
    FROM quotes_temp_df
    ON CONFLICT (symbol, ts, currency) DO UPDATE SET
        close = EXCLUDED.close,
        dividends = EXCLUDED.dividends,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        open = EXCLUDED.open,
        stock_splits = EXCLUDED.stock_splits,
        volume = EXCLUDED.volume;
