use crate::database::models::quote::Model as Quote;

pub enum SignalType {
    Unspecified=0,
    Up=1,
    Down=2,
    HighVolatility=3,
}

pub struct Signal {
    // Type of signal.
    pub category: SignalType,
    // When it was emmited.
    pub date: chrono::DateTime<chrono::Utc>,
    // For how long the signal remains valid.
    pub duration: chrono::Duration,
}

pub trait Strategy {

    /// Evaluate the strategy at the current time with the provided sorted ticks.
    /// Last element is the most recent.
    fn evaluate(&self, ticks: &[Quote] )-> Option<Signal>;
}
