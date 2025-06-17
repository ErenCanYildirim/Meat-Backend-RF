from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.auth.dependencies import require_admin
from app.config.database import get_db
from app.models.product import ProductCategory
from app.models.ml_models import ModelMetadata, Forecast, TrendAnalysis
from app.schemas.ml_schemas import (ForecastResponse, ModelStatusResponse,
                                    TrendResponse)
from app.services.ml_forecasting_service import MLForecastingService

router = APIRouter(prefix="/machine_learning", tags=["machine_learning"])


@router.post("/retrain", dependencies=[Depends(require_admin())])
def retrain_models(db: Session = Depends(get_db)):
    try:
        ml_service = MLForecastingService(db)
        results = ml_service.train_all_models()
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get(
    "/forecast/{product_category}",
    response_model=ForecastResponse,
    dependencies=[Depends(require_admin())],
)
def get_forecast(
    product_category: ProductCategory,
    horizon: str = "month",
    db: Session = Depends(get_db),
):
    if horizon not in ["month", "quarter"]:
        raise HTTPException(
            status_code=400, detail="Horizon must be 'month' or 'quarter'"
        )

    try:
        ml_service = MLForecastingService(db)
        result = ml_service.generate_forecast(product_category.value, horizon)
        return ForecastResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


@router.get(
    "/trends/{product_category}",
    response_model=TrendResponse,
    dependencies=[Depends(require_admin())],
)
def get_trends(
    product_category: ProductCategory,
    period: str = "30d",
    db: Session = Depends(get_db),
):
    """Get growth/decline trends for a product category"""
    period_mapping = {"30d": 30, "90d": 90}
    if period not in period_mapping:
        raise HTTPException(status_code=400, detail="Period must be '30d' or '90d'")

    try:
        ml_service = MLForecastingService(db)
        result = ml_service.calculate_trends(
            product_category.value, period_mapping[period]
        )
        return TrendResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.get(
    "/model/status",
    response_model=ModelStatusResponse,
    dependencies=[Depends(require_admin())],
)
def get_model_status(db: Session = Depends(get_db)):
    try:
        latest_models = {}
        for category in ProductCategory:
            models = (
                db.query(ModelMetadata)
                .filter(ModelMetadata.product_category == category.value)
                .order_by(desc(ModelMetadata.last_trained))
                .all()
            )

            if models:
                latest_models[category.value] = {
                    "models": [
                        {
                            "type": model.model_name,
                            "last_trained": model.last_trained.isoformat(),
                            "data_points": model.training_data_points,
                            "is_active": model.is_active,
                        }
                        for model in models
                    ]
                }
            else:
                latest_models[category.value] = {"models": [], "status": "no_models"}

        return ModelStatusResponse(models=latest_models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
