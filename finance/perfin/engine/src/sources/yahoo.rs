/// Module to fetch yahoo finance data.
pub mod historical {
    use rust_decimal::prelude::ToPrimitive;
    use tracing::info;
    use yfinance_rs::{Interval, Range, Ticker, YfClient};

    use crate::database::{models, operations::Client};

    /// Gets the data from yahoo finance and pushes it to the database
    /// provided.
    ///
    /// # Panics
    ///
    /// No panic expected..
    ///
    /// # Errors
    /// If an IO error occurs in db or in the web request.
    ///
    /// This function will return an error if .
    pub async fn fetch_and_upsert(
        db_client: Client,
        symbol: String,
    ) -> Result<(), Box<dyn std::error::Error>> {

        let client = YfClient::default();

        // Historical data
        let ticker = Ticker::new(&client, symbol.clone());
        // Get historical data for the last 6 months
        let history = ticker
            .history(Some(Range::M6), Some(Interval::D1), false)
            .await?;
        if let Some(last_bar) = history.last() {
            println!(
                "Last closing price: {} on timestamp {}",
                last_bar.ohlc.close, last_bar.ts
            );
        }

        // Get historical data for the last 6 months
        let history = ticker
            .history(Some(Range::M6), Some(Interval::D1), false)
            .await?;
        let size = history.len();
        let mut data: Vec<models::quote::Model> = vec![];
        for candle in history {
            let md = models::quote::Model {
                ts: candle.ts,
                symbol: symbol.clone(),
                currency: candle.currency.to_string(),
                open: candle.ohlc.open.into_inner(),
                close: candle.ohlc.close.into_inner(),
                high: candle.ohlc.high.into_inner(),
                low: candle.ohlc.low.into_inner(),
                volume: candle
                    .volume
                    .map_or(0, |x| x.as_decimal().round().to_i32().unwrap()), // no
                // real overflow possible.
                // Not sure of that
                // TODO: Check
                adjusted_close: candle
                    .close_unadj
                    .map_or(rust_decimal::Decimal::new(0, 1), |x| x.into_inner()),
            };

            data.push(md);
        }
        info!("Parsed {} points for {}", size, symbol);

        // Pushing to db.
        db_client.upsert_quotes(&data).await?;
        Ok(())
    }

    // Testing is too annoying here cause yt finance doenst use traits nor provide mocks.
}
