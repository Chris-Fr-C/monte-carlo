use core::fmt;

use rustler::Atom;
use sea_orm::DbErr;

// Really not motivated to find a cool name.
#[derive(Debug, Clone)]
pub struct AppError {
    msg: String,
}

impl AppError {
    pub fn new(msg: String) -> Self {
        Self { msg }
    }
}
impl std::error::Error for AppError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        None
    }

    fn description(&self) -> &str {
        "description() is deprecated; use Display"
    }

    fn cause(&self) -> Option<&dyn std::error::Error> {
        self.source()
    }
}
impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "invalid first item to double")
    }
}

impl From<DbErr> for AppError {
    fn from(value: DbErr) -> Self {
        AppError {
            msg: value.to_string(),
        }
    }
}
impl From<rustler::Error> for AppError {
    fn from(_: rustler::Error) -> Self {
        AppError {
            msg: "nif error".into(),
        }
    }
    // For convertion into elixir beam vm.
}

impl From<AppError> for rustler::Error {
    fn from(value: AppError) -> Self {
        rustler::Error::Term(Box::new(value.msg))
    }
}

impl From<Box<dyn std::error::Error>> for AppError {
    fn from(value: Box<dyn std::error::Error>) -> Self {
        AppError {
            msg: value.to_string(),
        }
    }
}
