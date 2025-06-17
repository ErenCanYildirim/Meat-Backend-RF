from typing import Dict, List
from pydantic import BaseModel


class ForecastResponse(BaseModel):
    status: str
    model_type: str = None
    horizon: str = None
    predictions: List[Dict] = []
    error: str = None


class TrendResponse(BaseModel):
    status: str
    product_category: str = None
    period_days: int = None
    percentage_change: float = None
    trend_direction: str = None
    current_period_total: int = None
    previous_period_total: int = None
    error: str = None


class ModelStatusResponse(BaseModel):
    models: Dict
    last_training: str = None
