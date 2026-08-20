use crate::database::models;
use crate::exceptions::AppError;
use crate::frames::quotes;
use chrono::{DateTime, Duration, Utc};
use polars::prelude::*;
use polars::{
    df,
    frame::{DataFrame, row::Row},
};
use sea_orm::{sea_query::OnConflict, *};
use std::{iter::from_fn, vec};

pub struct Client {
    pub db: DbConn,
}
impl Client {
    /// Creates the client with provided dsn.
    /// Recommended to use sqlite.
    ///
    /// # Errors
    /// If path or protocol is wrong.
    ///
    pub async fn new(db_url: &String) -> Result<Client, DbErr> {
        Ok(Client {
            db: Database::connect(db_url).await?,
        })
    }

    /// Insert quotes of a symbol into the database.
    ///
    /// # Errors
    /// If any problem occurs on the database connection or if some data cannot be updated.
    ///
    /// This function will return an error if .
    pub async fn upsert_quotes(&self, entries: &Vec<models::quote::Model>) -> Result<(), DbErr> {
        if entries.is_empty() {
            return Ok(());
        }
        // Building mutable models for seaorm.
        let active_models: Vec<models::quote::ActiveModel> = entries
            .iter()
            .map(|entry| entry.clone().into_active_model())
            .collect();

        // Then we upsert.
        models::quote::Entity::insert_many(active_models)
            .on_conflict(
                OnConflict::columns([
                    models::quote::Column::Symbol,
                    models::quote::Column::Ts,
                    models::quote::Column::Currency,
                ])
                .update_columns(vec![
                    models::quote::Column::Open,
                    models::quote::Column::High,
                    models::quote::Column::Low,
                    models::quote::Column::Close,
                    models::quote::Column::AdjustedClose,
                    models::quote::Column::Volume,
                ])
                .to_owned(),
            )
            .exec(&self.db)
            .await?;

        Ok(())
    }

    pub async fn get_quotes(
        &self,
        symbol: String,
        since: Duration,
        now: DateTime<Utc>,
    ) -> Result<Vec<models::quote::Model>, DbErr> {
        Ok(models::quote::Entity
            .select()
            .filter(
                models::quote::Column::Symbol.eq(symbol).and(
                    models::quote::Column::Ts
                        .gt(now - since)
                        .and(models::quote::Column::Ts.lte(now)),
                ),
            )
            .order_by_asc(models::quote::Column::Ts)
            .all(&self.db)
            .await?)
    }

    pub async fn get_quotes_df(
        &self,
        symbol: String,
        since: Duration,
        now: DateTime<Utc>,
    ) -> Result<LazyFrame, AppError> {
        let quotes = self.get_quotes(symbol, since, now).await?;

        let mut opens = Vec::with_capacity(quotes.len());
        let mut highs = Vec::with_capacity(quotes.len());
        let mut lows = Vec::with_capacity(quotes.len());
        let mut closes = Vec::with_capacity(quotes.len());
        let mut ts = Vec::with_capacity(quotes.len());
        let mut symbols = Vec::with_capacity(quotes.len());
        let mut currencies = Vec::with_capacity(quotes.len());
        let mut volumes = Vec::with_capacity(quotes.len());

        for q in quotes {
            opens.push(q.open);
            highs.push(q.high);
            lows.push(q.low);
            closes.push(q.close);
            ts.push(q.ts.timestamp_millis());
            symbols.push(q.symbol);
            currencies.push(q.currency);
            volumes.push(q.volume);
        }
        let d = df![
                quotes::Columns::Timestamp.as_str() => ts,
                quotes::Columns::Symbol.as_str() => symbols,
                quotes::Columns::Currency.as_str() => currencies,
                quotes::Columns::Open.as_str() => opens,
                quotes::Columns::High.as_str() => highs,
                quotes::Columns::Low.as_str() => lows,
                quotes::Columns::Close.as_str() => closes,
                quotes::Columns::Volume.as_str() => volumes,
        ];

        Ok(d?
            .lazy()
            .with_column(
                col(quotes::Columns::Timestamp)
                .cast(
                    DataType::Datetime(
                        TimeUnit::Milliseconds,
                        Some(TimeZone::UTC),
                    )
                )

            )
        )
    }
}


#[cfg(test)]
mod test{
    use super::*;
    use crate::{mocks::mock_client, sources::yahoo::historical::fetch_and_upsert};
    use chrono::TimeDelta;
use rust_decimal::Decimal;

    #[tokio::test]
    async fn test_upsert(){
        let client = mock_client();
        let start : DateTime<Utc> = chrono::DateTime::parse_from_rfc3339("2026-01-01T00:00:00+00:00").expect("Test time invalid").to_utc();
        let delta = TimeDelta::from_std(std::time::Duration::from_hours(24)).expect("Duration issues");
        let decimal = |x:f64| Decimal::new((x*100.0).floor() as i64, 2);
        let entries = vec![
            models::quote::Model{
                ts: start,
                open: decimal(10.00),
                high: decimal(11.0 ),
                low: decimal(9.0),
                close: decimal(10.5),
                symbol: "chris".into(),
                currency: "CHF".into(),
                volume: 10,
                adjusted_close: decimal(10.4),
            },

            models::quote::Model{
                ts: start+delta,
                open: decimal(10.00),
                high: decimal(11.0 ),
                low: decimal(9.0),
                close: decimal(10.5),
                symbol: "chris".into(),
                currency: "CHF".into(),
                volume: 10,
                adjusted_close: decimal(10.4),
            },

        ];
        client.upsert_quotes(&entries).await.expect("Issues upserting.") ;

    }
}
