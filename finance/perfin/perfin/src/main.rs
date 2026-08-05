mod database;
mod sources;
use clap::{Parser, Subcommand};
use sea_orm::{Database, DatabaseConnection};
use tracing::info;
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
        db: String
    },

    /// Single fetch of stock.
    SingleSync {
        #[arg(short, long, default_value = "NESN.SX")]
        symbol: String,

        #[arg(short, long, default_value = "sqlite://perfin.sqlite")]
        db: String
    },

    /// Run background queue processor
    Worker {
        #[arg(short, long, default_value_t = 4)]
        threads: usize,
        #[arg(short, long, default_value = "sqlite://perfin.sqlite")]
        db: String

    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    //

    match cli.command {
        Commands::Sync {db} => {
            let con = Database::connect(db).await?;
            database::init::setup_database(&con).await?;
        }
        Commands::SingleSync { symbol, db } => {
            info!("Starting single synchronization for {}", symbol);
        }

        _ => {
            todo!("Not implemented yet.")
        } // Commands:Worker { _ } => {
          //         todo!("Not implemented yet.")
          //     }
    }

    Ok(())
}
