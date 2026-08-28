from typing import Literal, TypedDict


class _YamlSymbolConfig(TypedDict):
    symbol: str
    currency: Literal["CHF", "USD", "EUR"]

class YamlConfig(TypedDict):
    stocks: list[_YamlSymbolConfig]
    start_date: str
