use crate::{
    database::{self, operations::Client},
    exceptions::AppError,
    sources,
};
use once_cell::sync::Lazy;
#[doc = r"Module to connect rust to my elixir beam orchestrator system."]
use rustler::NifResult;
use sea_orm::Database;
use tokio::runtime::Runtime;

// Global tokio runtime.
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap()
});

// the nif gotta be in sync
#[rustler::nif(schedule="DirtyIo")]
pub fn fetch(db_url: String, symbol: String) -> NifResult<()> {
    // 4. Use the runtime to await/block on the async function
    let res: Result<(), AppError> = RUNTIME.block_on(async {
        // something_async().await
        let db_client = Client::new(&db_url).await?;
        sources::yahoo::historical::fetch_and_upsert(db_client, symbol).await?;

        Ok(())
    });
    res?;
    Ok(())
}

#[rustler::nif(schedule="DirtyIo")]
pub fn init_db(db_url: String) -> NifResult<()> {
    let result = RUNTIME.block_on(async {
        let con = Database::connect(db_url)
            .await
            .map_err(|err| AppError::from(err))?;
        database::init::setup_database(&con).await?;
        Ok(())
    });
    result
}


fn load(_env: rustler::Env, _term: rustler::Term) -> bool {
    true
}

rustler::init!("Elixir.Orchestration.Engine", load = load);
