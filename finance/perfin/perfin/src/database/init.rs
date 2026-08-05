/// Life is too short to do proper versioning for a local db.
/// Just build or clean the db cause it's small anyway.
use sea_orm::{ConnectionTrait, DatabaseConnection, DbBackend, DbErr, EntityTrait, Schema};

use crate::database::models::quote;

pub async fn setup_database(db: &DatabaseConnection) -> Result<(), DbErr> {
    if db.get_database_backend() == DbBackend::Sqlite {
        // Use execute_unprepared for raw SQL string commands like PRAGMA
        db.execute_unprepared("PRAGMA foreign_keys = ON;").await?;
    }

    let schema = Schema::new(DbBackend::Sqlite);

    create_table(db, &schema, quote::Entity).await?;

    Ok(())
}

async fn create_table<E>(
    db: &DatabaseConnection,
    schema: &Schema,
    entity: E,
) -> Result<(), DbErr>
where
    E: EntityTrait,
{
    let mut create_table_stmt = schema.create_table_from_entity(entity);
    create_table_stmt.if_not_exists();

    // TableCreateStatement implements StatementBuilder directly
    db.execute(&create_table_stmt).await?;

    Ok(())
}
