//use yfinance_rs::{Interval, Range, Ticker, YfClient};



// async fn main() -> Result<(), Box<dyn std::error::Error>> {
//     let client = YfClient::default();
//     let ticker = Ticker::new(client, "AAPL".to_string());
//
//     // Get the latest quote
//     let quote = ticker.quote().await?;
//     println!("Latest price for AAPL: ${:.2}", quote.regular_market_price.unwrap_or(0.0));
//
//     // Get historical data for the last 6 months
//     let history = ticker.history(Some(Range::M6), Some(Interval::D1), false).await?;
//     if let Some(last_bar) = history.last() {
//         println!("Last closing price: ${:.2} on {}", last_bar.close, last_bar.ts);
//     }
//
//     Ok(())
// }
