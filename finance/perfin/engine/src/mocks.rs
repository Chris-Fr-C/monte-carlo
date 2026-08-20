use sea_orm::MockDatabase;
pub fn mock_client() -> crate::database::operations::Client {
    let db = MockDatabase::new(sea_orm::DatabaseBackend::Sqlite);
    super::Client {
        db: db.into_connection(),
    }
}
