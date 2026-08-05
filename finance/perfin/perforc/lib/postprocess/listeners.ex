defmodule PostProcess.Listener do
  use GenServer
  # https://elixir.hexdocs.pm/GenServer.html
  def start_link(_), do: GenServer.start_link(__MODULE__, [])

  @impl true
  def init(_) do
    # Register to receive stock updates.
    Registry.register(App.StockRegistry, "stock_updates", [])
    # result + initial state
    {:ok, %{}}
  end

  def handle_info({:stock_data, ticker, data}, state) do
    IO.inspect({ticker, data}, label: "Received Update")
    {:noreply, state}
  end
end
