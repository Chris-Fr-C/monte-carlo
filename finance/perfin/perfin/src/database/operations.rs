use crate::database::models;
use sea_orm::{
    sea_query::OnConflict,
    *,
};

pub async fn upsert_quotes(db: &DbConn, entries: &Vec<models::quote::Model>) -> Result<(), DbErr> {
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
        .exec(db)
        .await?;

    Ok(())
}
