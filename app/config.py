"""Load application configuration from config.yaml."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class OfferConfig(BaseModel):
    name: str
    threshold: float = Field(ge=0)
    discount_percent: float = Field(ge=0, le=100)


class TaxConfig(BaseModel):
    name: str
    percent: float = Field(ge=0, le=100)


class CouponConfig(BaseModel):
    type: Literal["percent", "flat"]
    value: float = Field(ge=0)
    min_subtotal: float = Field(ge=0, default=0)


class AppConfig(BaseModel):
    currency: str
    currency_symbol: str
    offer: OfferConfig
    tax: TaxConfig
    coupons: dict[str, CouponConfig] = Field(default_factory=dict)


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
