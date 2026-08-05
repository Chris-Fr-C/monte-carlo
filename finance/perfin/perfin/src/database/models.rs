pub mod quote {
    use rust_decimal::Decimal;
    use chrono::{DateTime, Utc};
    use sea_orm::entity::prelude::*;

    #[derive(Clone, Debug, PartialEq, DeriveEntityModel)]
    #[sea_orm(table_name = "quote")]
    pub struct Model {
        #[sea_orm(primary_key, indexed)]
        pub ts: DateTime<Utc>,
        #[sea_orm(primary_key, indexed)]
        pub symbol: String,
        #[sea_orm(primary_key)]
        pub currency: String,

        #[sea_orm()]
        pub open: Decimal,
        #[sea_orm()]
        pub high: Decimal,
        #[sea_orm()]
        pub low: Decimal,
        #[sea_orm()]
        pub close: Decimal,
        #[sea_orm()]
        pub adjusted_close: Decimal,
        #[sea_orm()]
        pub volume: i32,
    }

    #[derive(Copy, Clone, Debug, EnumIter, DeriveRelation)]
    pub enum Relation {}

    impl ActiveModelBehavior for ActiveModel {}
}
