defmodule Orchestration.Supervisor do
  use Supervisor

  def start_link(init_arg) do
    Supervisor.start_link(__MODULE__, init_arg, name: __MODULE__)
  end

  @impl true
  def init(_init_arg) do
    children = [
      {Registry, keys: :duplicate, name: Orchestration.StockRegistry},
      {Task.Supervisor, name: Orchestration.FetcherSupervisor},
      Orchestration.StockScheduler
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end
end
