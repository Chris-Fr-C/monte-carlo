/// Module to connect rust to my elixir beam orchestrator system.
use rustler::NifResult;
use once_cell::sync::Lazy;
use tokio::runtime::Runtime;

// 1. Create a global Tokio runtime so you don't recreate it every call
static RUNTIME: Lazy<Runtime> = Lazy::new(|| {
    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .unwrap()
});

// 2. Your actual async Rust function

// 3. The Rustler NIF wrapper (Regular `fn`, NOT `async fn`)
// #[rustler::nif(schedule = "DirtyIo")]
// pub fn wrapper() -> NifResult<String> {
//     // 4. Use the runtime to await/block on the async function
//     let result = RUNTIME.block_on(async {
//         something_async().await
//     });
//
//     Ok(result)
// }
