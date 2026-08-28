INSERT INTO signals BY NAME
SELECT ts, symbol, name, category, confidence
FROM signals_temp_df
ON CONFLICT (ts, symbol, name) DO UPDATE SET
    category = EXCLUDED.category,
    confidence = EXCLUDED.confidence;
