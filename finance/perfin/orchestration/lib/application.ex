defmodule Orchestration.Application do
  use Application

  @impl true
  def start(_type, _args) do
    # This calls your Supervisor module below
    Orchestration.Supervisor.start_link([])
  end
end
