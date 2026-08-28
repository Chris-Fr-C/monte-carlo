from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
import os
import pathlib
import duckdb
import fintools.config as config
import loguru
import yaml
from typing import cast
def _get_config(reference: pathlib.Path) -> config.YamlConfig:
    with open(reference, "r") as fi:
        cfg: config.YamlConfig = cast(config.YamlConfig, yaml.safe_load(fi))
    return cfg

def _ref_path()->pathlib.Path:
    default = pathlib.Path() / "data" / "reference.yaml"
    if os.environ.get("FINTOOLS_REF_FILE"):
        return pathlib.Path(os.environ["FINTOOLS_REF_FILE"])
    return default

class Container(containers.DeclarativeContainer):
    db_path: providers.Singleton[pathlib.Path] = providers.Singleton(pathlib.Path, os.environ.get("FINTOOLS_DB_FILE", "./fintools.duckdb"))
    connection: providers.Factory[duckdb.DuckDBPyConnection] = providers.Factory(duckdb.connect, database=db_path)
    reference_path:providers.Object[pathlib.Path] = providers.Object(
            _ref_path()
        )
    reference: providers.Singleton[config.YamlConfig] = providers.Singleton(_get_config, reference=reference_path)
    logger: providers.Singleton["loguru.Logger"] = providers.Singleton(lambda: loguru.logger)
