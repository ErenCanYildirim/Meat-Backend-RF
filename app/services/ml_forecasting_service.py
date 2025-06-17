import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

warnings.filterwarnings("ignore")

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.models.ml_models import Forecast, ModelMetadata, TrendAnalysis
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductCategory


class MLForecastingService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.models = {}
        self.model_version = datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_historical_data(
        self, product_category: str, days_back: int = 365
    ) -> pd.DataFrame:
        cutoff_date = datetime.now() - timedelta(days=days_back)

        query = (
            self.db.query(
                func.date(Order.order_date).label("date"),
                func.sum(OrderItem.quantity).label("total_quantity"),
            )
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.category == product_category)
            .filter(Order.order_date >= cutoff_date)
            .group_by(func.date(Order.order_date))
            .order_by(func.date(Order.order_date))
        )

        df = pd.read_sql(query.statement, self.db.bind)

        if df.empty:
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
        df = df.reindex(date_range, fill_value=0)

        return df

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        features_df = df.copy()
        features_df["day_of_week"] = features_df.index.dayofweek
        features_df["day_of_month"] = features_df.index.day
        features_df["month"] = features_df.index.month
        features_df["quarter"] = features_df.index.quarter
        features_df["days_since_start"] = (
            features_df.index - features_df.index.min()
        ).days

        features_df["seasonal_sin"] = np.sin(
            2 * np.pi * features_df["days_since_start"] / 90
        )
        features_df["seasonal_cos"] = np.cos(
            2 * np.pi * features_df["days_since_start"] / 90
        )

        return features_df

    def train_sarima_model(self, df: pd.DataFrame, product_category: str) -> Dict:
        if len(df) < 90:
            return {
                "error": "Insufficient data for SARIMA model (need at least 90 days)"
            }

        try:
            model = SARIMAX(
                df["total_quantity"],
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 90),
                enforce_stationarity=False,
                enforce_invertibility=False,
            )

            fitted_model = model.fit(disp=False)

            fitted_values = fitted_model.fittedvalues
            mae = mean_absolute_error(df["total_quantity"], fitted_values)
            rmse = np.sqrt(mean_squared_error(df["total_quantity"], fitted_values))

            model_key = f"sarima_{product_category}"
            self.models[model_key] = fitted_model

            return {
                "model_type": "SARIMA",
                "status": "success",
                "mae": mae,
                "rmse": rmse,
                "data_points": len(df),
            }

        except Exception as e:
            return {"error": f"SARIMA training failed: {str(e)}"}

    def train_linear_model(self, df: pd.DataFrame, product_category: str) -> Dict:

        if len(df) < 30:
            return {
                "error": "Insufficient data for linear model (need at least 30 days)"
            }

        try:
            features_df = self.prepare_features(df)

            feature_cols = [
                "day_of_week",
                "day_of_month",
                "month",
                "quarter",
                "days_since_start",
                "seasonal_sin",
                "seasonal_cos",
            ]

            X = features_df[feature_cols]
            y = features_df["total_quantity"]

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = LinearRegression()
            model.fit(X_scaled, y)

            y_pred = model.predict(X_scaled)
            mae = mean_absolute_error(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))

            model_key = f"linear_{product_category}"
            self.models[model_key] = {"model": model, "scaler": scaler}

            return {
                "model_type": "Linear",
                "status": "success",
                "mae": mae,
                "rmse": rmse,
                "data_points": len(df),
            }

        except Exception as e:
            return {"error": f"Linear model training failed: {str(e)}"}

    def generate_forecast(self, product_category: str, horizon: str) -> Dict:
        days_ahead = 30 if horizon == "month" else 90

        # Try SARIMA first, fall back to linear model if it fails
        sarima_key = f"sarima_{product_category}"
        linear_key = f"linear_{product_category}"

        if sarima_key in self.models:
            return self._forecast_sarima(product_category, days_ahead, horizon)
        elif linear_key in self.models:
            return self._forecast_linear(product_category, days_ahead, horizon)
        else:
            return {"error": "No trained model available for this category"}

    def _forecast_sarima(
        self, product_category: str, days_ahead: int, horizon: str
    ) -> Dict:
        model_key = f"sarima_{product_category}"
        model = self.models[model_key]

        try:
            forecast = model.forecast(steps=days_ahead)
            forecast_ci = model.get_forecast(steps=days_ahead).conf_int()

            start_date = datetime.now().date() + timedelta(days=1)
            dates = [start_date + timedelta(days=i) for i in range(days_ahead)]

            predictions = []
            for i, date in enumerate(dates):
                predictions.append(
                    {
                        "date": date.isoformat(),
                        "predicted_quantity": float(forecast.iloc[i]),
                        "confidence_lower": float(forecast_ci.iloc[i, 0]),
                        "confidence_upper": float(forecast_ci.iloc[i, 1]),
                    }
                )

            self._save_forecasts(product_category, predictions, horizon)

            return {
                "status": "success",
                "model_type": "SARIMA",
                "horizon": horizon,
                "predictions": predictions,
            }

        except Exception as e:
            return {"error": f"SARIMA forecasting failed: {str(e)}"}

    def _forecast_linear(
        self, product_category: str, days_ahead: int, horizont: str
    ) -> Dict:
        model_key = f"linear_{product_category}"
        model_data = self.models[model_key]
        model = model_data["model"]
        scaler = model_data["scaler"]

        try:
            start_date = datetime.now().date() + timedelta(days=1)
            dates = [start_date + timedelta(days=i) for i in range(days_ahead)]

            future_features = []
            for i, date in enumerate(dates):
                dt = datetime.combine(date, datetime.min.time())
                features = [
                    dt.weekday(),
                    dt.day,
                    dt.month,
                    dt.quarter,
                    i + 1,
                    np.sin(2 * np.pi * (i + 1) / 90),
                    np.cos(2 * np.pi * (i + 1) / 90),
                ]
                future_features.append(features)

            X_future = np.array(future_features)
            X_future_scaled = scaler.transform(X_future)

            predictions_raw = model.predict(X_future_scaled)

            residual_std = np.std(predictions_raw) * 0.2  # simple confidence interval

            predictions = []
            for i, date in enumerate(dates):
                pred_value = max(0, predictions_raw[i])  # Ensure non-negative
                predictions.append(
                    {
                        "date": date.isoformat(),
                        "predicted_quantity": float(pred_value),
                        "confidence_lower": float(
                            max(0, pred_value - 1.96 * residual_std)
                        ),
                        "confidence_upper": float(pred_value + 1.96 * residual_std),
                    }
                )

            # Store in database
            self._save_forecasts(product_category, predictions, horizon)

            return {
                "status": "success",
                "model_type": "Linear",
                "horizon": horizon,
                "predictions": predictions,
            }

        except Exception as e:
            return {"error": f"Linear forecasting failed: {str(e)}"}

    def _save_forecasts(
        self, product_category: str, predictions: List[Dict], horizon: str
    ):
        try:
            self.db.query(Forecast).filter(
                Forecast.product_category == product_category,
                Forecast.horizon_type == horizon,
            ).delete()

            for pred in predictions:
                forecast = Forecast(
                    product_category=product_category,
                    forecast_date=datetime.fromisoformat(pred["date"]),
                    predicted_quantity=pred["predicted_quantity"],
                    confidence_lower=pred["confidence_lower"],
                    confidence_upper=pred["confidence_upper"],
                    horizon_type=horizon,
                    model_version=self.model_version,
                )
                self.db.add(forecast)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving forecasts: {e}")

    def calculate_trends(self, product_category: str, period_days: int) -> Dict:

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            comparison_start = start_date - timedelta(days=period_days)

            current_query = (
                self.db.query(func.sum(OrderItem.quantity))
                .join(Order, OrderItem.order_id == Order.id)
                .join(Product, OrderItem.product_id == Product.id)
                .filter(Product.category == product_category)
                .filter(Order.order_date >= start_date)
                .filter(Order.order_date <= end_date)
            )
            current_total = current_query.scalar() or 0

            previous_query = (
                self.db.query(func.sum(OrderItem.quantity))
                .join(Order, OrderItem.order_id == Order.id)
                .join(Product, OrderItem.product_id == Product.id)
                .filter(Product.category == product_category)
                .filter(Order.order_date >= comparison_start)
                .filter(Order.order_date < start_date)
            )
            previous_total = previous_query.scalar() or 0

            if previous_total == 0:
                percentage_change = 100.0 if current_total > 0 else 0.0
            else:
                percentage_change = (
                    (current_total - previous_total) / previous_total
                ) * 100

            if abs(percentage_change) < 5:
                trend_direction = "stable"
            elif percentage_change > 0:
                trend_direction = "growing"
            else:
                trend_direction = "declining"

            trend_analysis = TrendAnalysis(
                product_category=product_category,
                period_days=period_days,
                percentage_change=percentage_change,
                trend_direction=trend_direction,
                start_date=start_date,
                end_date=end_date,
            )

            self.db.query(TrendAnalysis).filter(
                TrendAnalysis.product_category == product_category,
                TrendAnalysis.period_days == period_days,
            ).delete()

            self.db.add(trend_analysis)
            self.db.commit()

            return {
                "status": "success",
                "product_category": product_category,
                "period_days": period_days,
                "percentage_change": round(percentage_change, 2),
                "trend_direction": trend_direction,
                "current_period_total": current_total,
                "previous_period_total": previous_total,
            }

        except Exception as e:
            self.db.rollback()
            return {"error": f"Trend calculation failed: {str(e)}"}

    def train_all_models(self) -> Dict:
        results = {}

        for category in ProductCategory:
            category_results = {"sarima": None, "linear": None}

            df = self.get_historical_data(category.value)

            if df.empty:
                category_results["error"] = "No historical data available"
            else:
                sarima_result = self.train_sarima_model(df, category.value)
                category_results["sarima"] = sarima_result

                linear_result = self.train_linear_model(df, category.value)
                category_results["linear"] = linear_result

                self._save_model_metadata(category.value, sarima_result, linear_result)

            results[category.value] = category_results
        return results

    def _save_model_metadata(
        self, category: str, sarima_result: Dict, linear_result: Dict
    ):
        try:
            self.db.query(ModelMetadata).filter(
                ModelMetadata.product_category == category
            ).delete()

            if "error" not in sarima_result:
                sarima_metadata = ModelMetadata(
                    model_name="SARIMA",
                    product_category=category,
                    training_data_points=sarima_result.get("data_points", 0),
                    model_params=json.dumps(
                        {"order": "(1,1,1)", "seasonal_order": "(1,1,1,90)"}
                    ),
                    performance_metrics=json.dumps(
                        {
                            "mae": sarima_result.get("mae", 0),
                            "rmse": sarima_result.get("rmse", 0),
                        }
                    ),
                    is_active=True,
                )
                self.db.add(sarima_metadata)

            if "error" not in linear_result:
                linear_metadata = ModelMetadata(
                    model_name="Linear",
                    product_category=category,
                    training_data_points=linear_result.get("data_points", 0),
                    model_params=json.dumps({"features": "time_based_seasonal"}),
                    performance_metrics=json.dumps(
                        {
                            "mae": linear_result.get("mae", 0),
                            "rmse": linear_result.get("rmse", 0),
                        }
                    ),
                    is_active="error" in sarima_result,
                )
                self.db.add(linear_metadata)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving model metadata: {e}")
