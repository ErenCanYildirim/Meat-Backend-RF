from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.config.database import get_db
from app.models.ml_models import Forecast, ModelMetadata, TrendAnalysis
from app.models.product import ProductCategory
from app.schemas.ml_schemas import (CustomerClusterResponse, CustomerFeatures,
                                    ForecastResponse, ModelStatusResponse,
                                    TrendResponse)
from app.services.ml_clustering_service import (analyze_clusters,
                                                create_visualization,
                                                extract_customer_features,
                                                perform_clustering)
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


@router.get(
    "/customer-clusters/summary",
    dependencies=[Depends(require_admin())],
)
async def get_cluster_summary(db: Session = Depends(get_db), days_back: int = 365):
    df = extract_customer_features(db, days_back)
    clusters, _, _, _ = perform_clustering(df)
    cluster_analysis = analyze_clusters(df, clusters)

    summary = {}
    for cluster_name, data in cluster_analysis.items():
        summary[cluster_name] = {
            "type": data["cluster_type"],
            "size": data["size"],
            "percentage": round(data["percentage"], 1),
            "description": data["description"],
        }

    return summary


@router.get(
    "/customer-clusters",
    response_model=CustomerClusterResponse,
    dependencies=[Depends(require_admin())],
)
async def analyze_customer_clusters(
    db: Session = Depends(get_db), days_back: int = 365, n_clusters: int = 4
):
    """
    -> customer segmentation based on purchasing behavior
    -> identification of high-value custom.
    -> at risk customer detection
    -> category preference analysis
    """

    try:
        df = extract_customer_features(db, days_back)

        if len(df) < n_clusters:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough customers ({len(df)}) for {n_clusters} clusters",
            )

        clusters, scaler, kmeans, X_scaled = perform_clustering(df, n_clusters)

        cluster_analysis = analyze_clusters(df, clusters)

        visualization_b64 = create_visualization(df, clusters)

        df["cluster"] = clusters
        customer_segments = []
        for _, row in df.iterrows():
            customer_segments.append(
                {
                    "email": row["user_email"],
                    "cluster_id": int(row["cluster"]),
                    "cluster_type": cluster_analysis[f'cluster_{row["cluster"]}'][
                        "cluster_type"
                    ],
                    "total_orders": int(row["total_orders"]),
                    "total_quantity": int(row["total_quantity"]),
                    "favorite_category": row["favorite_category"],
                    "days_since_last_order": int(row["days_since_last_order"]),
                    "order_frequency": round(row["order_frequency"], 2),
                }
            )

        return CustomerClusterResponse(
            cluster_insights=cluster_analysis,
            customer_segments=customer_segments,
            visualization_base64=visualization_b64,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Clustering analysis failed: {str(e)}"
        )
