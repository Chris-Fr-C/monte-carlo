// Declaring columns of the dataframes we will use.

pub mod quotes {
    use polars::datatypes::PlSmallStr;

    // For polar dataframes.
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub enum Columns {
        Open,
        High,
        Low,
        Close,
        Timestamp,
        Symbol,
        Currency,
        Volume,
    }

    impl Columns {
        pub const fn as_str(self) -> &'static str {
            match self {
                Self::Open => "open",
                Self::High => "high",
                Self::Low => "low",
                Self::Close => "close",
                Self::Timestamp => "timestamp",
                Self::Symbol => "symbol",
                Self::Currency => "currency",
                Self::Volume => "volume",
            }
        }
    }
    /// Just to make it easier to use with lazy col:
    /// >>> df.with_column(col(Columns::Timestamp).cast(etc...))
    impl Into<PlSmallStr> for Columns {
        fn into(self) -> PlSmallStr {
            self.as_str().into()
        }
    }
}
