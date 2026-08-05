defmodule Orchestration.Env do
  def db_path() do
    File.cwd! <> "/perfin.sqlite"
  end

 def db_url() do
    "sqlite://" <> db_path()
  end
end
