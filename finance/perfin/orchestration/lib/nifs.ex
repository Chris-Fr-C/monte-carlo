defmodule Orchestration.Engine do
    # I use the path so i dont have to keep the rust code into native/ folder.
    use Rustler, otp_app: :orchestration, crate: :engine, path: "../engine"


  def fetch(_db_url, _symbol) do
    :erlang.nif_error(:nif_not_loaded)
  end
  def init_db(_db_url) do
    :erlang.nif_error(:nif_not_loaded)
  end
end
