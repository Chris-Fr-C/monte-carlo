defmodule Orchestration.Supervisor do
  def start(_type, _args) do
    children = [
      {Registry, keys: :duplicate, name: Orchestration.StockRegistry},
      {Task.Supervisor, name: Orchestration.FetcherSupervisor},
      Orchestration.StockScheduler
    ]

    opts = [strategy: :one_for_one, name: Orchestration.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
