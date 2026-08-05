defmodule PerforcTest do
  use ExUnit.Case
  doctest Perforc

  test "greets the world" do
    assert Perforc.hello() == :world
  end
end
