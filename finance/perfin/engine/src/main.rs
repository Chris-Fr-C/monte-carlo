mod database;
mod sources;
mod exceptions;
mod strategy;
mod mocks;
mod frames;
use clap::{Parser, Subcommand};
use sea_orm::Database;
use tracing::info;


use crate::database::operations::Client;

#[derive(Parser)]
#[command(name = "my_app", author, version, about = "CLI app with multiple entrypoints", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Fetch data for watched symbols.
    Sync {
        #[arg(short, long, default_value = "sqlite://perfin.sqlite")]
        db: String,
    },

    /// Single fetch of stock.
    SingleSync {
        #[arg(short, long, default_value = "NESN.SX")]
        symbol: String,

        #[arg(short, long, default_value = "sqlite://perfin.sqlite")]
        db: String,
    },

    /// Run background queue processor
    Worker {
        #[arg(short, long, default_value_t = 4)]
        threads: usize,
        #[arg(short, long, default_value = "sqlite://perfin.sqlite")]
        db: String,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    //

    match cli.command {
        Commands::Sync { db } => {
            let con = Database::connect(db).await?;
            database::init::setup_database(&con).await?;
        }
        Commands::SingleSync { symbol, db } => {
            let con = Database::connect(db.clone()).await?;
            info!("Starting single synchronization for {}", symbol);
            database::init::setup_database(&con).await?;

            let db_client = Client::new(&db).await?;
            sources::yahoo::historical::fetch_and_upsert(db_client, "NESN.SW".to_string()).await?;
        }

        _ => {
            todo!("Not implemented yet.")
        } // Commands:Worker { _ } => {
          //         todo!("Not implemented yet.")
          //     }
    }

    Ok(())
}
