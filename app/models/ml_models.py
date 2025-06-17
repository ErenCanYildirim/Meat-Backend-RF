from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    product_category = Column(String, nullable=False, index=True)
    forecast_date = Column(DateTime, nullable=False)
    predicted_quantity = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=False)
    confidence_upper = Column(Float, nullable=False)
    horizon_type = Column(String, nullable=False)  # 'month' or 'quarter'
    created_at = Column(DateTime, default=func.now())
    model_version = Column(String, nullable=False)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    product_category = Column(String, nullable=False)
    last_trained = Column(DateTime, default=func.now())
    training_data_points = Column(Integer, nullable=False)
    model_params = Column(Text)  # JSON string of model parameters
    performance_metrics = Column(Text)  # JSON string of metrics
    is_active = Column(Boolean, default=True)


class TrendAnalysis(Base):
    __tablename__ = "trend_analysis"

    id = Column(Integer, primary_key=True, index=True)
    product_category = Column(String, nullable=False, index=True)
    period_days = Column(Integer, nullable=False)  # 30 or 90
    percentage_change = Column(Float, nullable=False)
    trend_direction = Column(String, nullable=False)  # 'growing', 'declining', 'stable'
    calculated_at = Column(DateTime, default=func.now())
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
