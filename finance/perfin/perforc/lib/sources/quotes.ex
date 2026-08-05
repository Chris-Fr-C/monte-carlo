defmodule  App.StockScheduler do
  @moduledoc """
  This aims to provide a scheduler that will run nifs and fetch data twice per day.
  """
use GenServer

  @twelve_hours_ms 12 * 60 * 60 * 1000
  @default_stocks ["NESN.SW", ]

  # GenServer api
  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  # The callbacks
  @impl true
  def init(_opts) do
    # todo: Schedule the first run immediately (or adjust to a specific UTC time)
    send(self(), :fetch_all)
    {:ok, %{stocks: @default_stocks}}
  end

  @impl true
  def handle_info(:fetch_all, state) do
    # Kick off asynchronous tasks for each stock so one slow NIF doesn't block the rest
    # here i call one nif per stock.
    Enum.each(state.stocks, fn ticker ->
      Task.Supervisor.start_child(App.FetcherSupervisor, fn ->
        fetch_and_notify(ticker)
      end)
    end)

    # Schedule next run in 12 hours
    Process.send_after(self(), :fetch_all, @twelve_hours_ms)
    {:noreply, state}
  end

  defp fetch_and_notify(ticker) do
    # 1. Call your Rust NIF
    case App.RustNif.fetch_stock_data(ticker) do
      {:ok, data} ->
        # 2. Dispatch notification via Registry
        Registry.dispatch(App.StockRegistry, "stock_updates", fn entries ->
          for {pid, _value} <- entries, do: send(pid, {:stock_data, ticker, data})
        end)

      {:error, reason} ->
        # Log error; Task dies cleanly without killing the scheduler
        Logger.error("Failed to fetch #{ticker}: #{inspect(reason)}")
    end
  end
end


defmodule App.StockFetcher do
  @moduledoc """
  This will supervise the run of a nif to fetch data for a specific stock.
  """
end
