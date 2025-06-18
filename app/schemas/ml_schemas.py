from typing import Any, Dict, List

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


# clustering schemas
class CustomerClusterResponse(BaseModel):
    cluster_insights: Dict[str, Any]
    customer_segments: List[Dict[str, Any]]
    visualization_base64: str


class CustomerFeatures(BaseModel):
    user_email: str
    total_orders: int
    total_quantity: int
    avg_order_quantity: float
    days_since_last_order: int
    favorite_category: str
    category_diversity: float
    chicken_ratio: float
    beef_ratio: float
    veal_ratio: float
    lamb_ratio: float
    other_ratio: float
    order_frequency: float
