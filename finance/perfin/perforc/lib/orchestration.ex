defmodule orchestration do
  def start(_type, _args) do
    children = [
      {Registry, keys: :duplicate, name: App.StockRegistry},
      {Task.Supervisor, name: App.FetcherSupervisor},
      App.StockScheduler
    ]

    opts = [strategy: :one_for_one, name: App.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
