import base64
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderState
from app.models.product import Product, ProductCategory
from app.schemas.ml_schemas import CustomerClusterResponse, CustomerFeatures


def extract_customer_features(db: Session, days_back: int = 365) -> pd.DataFrame:

    cutoff_date = datetime.now() - timedelta(days=days_back)

    query = (
        db.query(
            Order.user_email, Order.order_date, OrderItem.quantity, Product.category
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(Order.order_date >= cutoff_date, Order.state != OrderState.EMAIL_SENT)
    )

    df = pd.read_sql(query.statement, db.bind)

    if df.empty:
        raise HTTPException(status_code=404, detail="No order data found")

    customer_features = []

    for email in df["user_email"].unique():
        customer_data = df[df["user_email"] == email]

        total_orders = len(customer_data["order_date"].unique())
        total_quantity = customer_data["quantity"].sum()
        avg_order_quantity = total_quantity / total_orders

        last_order = customer_data["order_date"].max()
        days_since_last = (datetime.now() - last_order).days
        first_order = customer_data["order_date"].min()
        customer_lifetime_days = max((last_order - first_order).days, 1)
        order_frequency = (total_orders / customer_lifetime_days) * 30

        category_counts = customer_data.groupby("category")["quantity"].sum()
        total_cat_quantity = category_counts.sum()

        chicken_ratio = (
            category_counts.get(ProductCategory.CHICKEN, 0) / total_cat_quantity
        )
        beef_ratio = category_counts.get(ProductCategory.BEEF, 0) / total_cat_quantity
        veal_ratio = category_counts.get(ProductCategory.VEAL, 0) / total_cat_quantity
        lamb_ratio = category_counts.get(ProductCategory.LAMB, 0) / total_cat_quantity
        other_ratio = category_counts.get(ProductCategory.OTHER, 0) / total_cat_quantity

        category_diversity = len(category_counts[category_counts > 0]) / len(
            ProductCategory
        )

        favorite_category = (
            category_counts.idxmax().value
            if not category_counts.empty
            else ProductCategory.OTHER.value
        )

        customer_features.append(
            {
                "user_email": email,
                "total_orders": total_orders,
                "total_quantity": total_quantity,
                "avg_order_quantity": avg_order_quantity,
                "days_since_last_order": days_since_last,
                "favorite_category": favorite_category,
                "category_diversity": category_diversity,
                "chicken_ratio": chicken_ratio,
                "beef_ratio": beef_ratio,
                "veal_ratio": veal_ratio,
                "lamb_ratio": lamb_ratio,
                "other_ratio": other_ratio,
                "order_frequency": order_frequency,
            }
        )

    return pd.DataFrame(customer_features)


def perform_clustering(df: pd.DataFrame, n_clusters: int = 4) -> tuple:

    feature_columns = [
        "total_orders",
        "total_quantity",
        "avg_order_quantity",
        "days_since_last_order",
        "category_diversity",
        "order_frequency",
        "chicken_ratio",
        "beef_ratio",
        "veal_ratio",
        "lamb_ratio",
        "other_ratio",
    ]

    X = df[feature_columns].copy()
    X = X.fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    return clusters, scaler, kmeans, X_scaled


def create_visualization(df: pd.DataFrame, clusters: np.ndarray) -> str:
    """returns visualization of clusters as base64 string"""

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Customer Segmentation Analysis", fontsize=16)

    # Add cluster labels to dataframe
    df_viz = df.copy()
    df_viz["cluster"] = clusters

    # 1. Total Orders vs Total Quantity
    axes[0, 0].scatter(
        df_viz["total_orders"],
        df_viz["total_quantity"],
        c=clusters,
        cmap="viridis",
        alpha=0.7,
    )
    axes[0, 0].set_xlabel("Total Orders")
    axes[0, 0].set_ylabel("Total Quantity")
    axes[0, 0].set_title("Orders vs Quantity by Cluster")

    # 2. Order Frequency vs Days Since Last Order
    axes[0, 1].scatter(
        df_viz["order_frequency"],
        df_viz["days_since_last_order"],
        c=clusters,
        cmap="viridis",
        alpha=0.7,
    )
    axes[0, 1].set_xlabel("Order Frequency (orders/month)")
    axes[0, 1].set_ylabel("Days Since Last Order")
    axes[0, 1].set_title("Frequency vs Recency by Cluster")

    # 3. Category Diversity vs Average Order Quantity
    axes[1, 0].scatter(
        df_viz["category_diversity"],
        df_viz["avg_order_quantity"],
        c=clusters,
        cmap="viridis",
        alpha=0.7,
    )
    axes[1, 0].set_xlabel("Category Diversity")
    axes[1, 0].set_ylabel("Average Order Quantity")
    axes[1, 0].set_title("Diversity vs Order Size by Cluster")

    # 4. Cluster distribution
    cluster_counts = pd.Series(clusters).value_counts().sort_index()
    axes[1, 1].bar(
        range(len(cluster_counts)),
        cluster_counts.values,
        color=plt.cm.viridis(np.linspace(0, 1, len(cluster_counts))),
    )
    axes[1, 1].set_xlabel("Cluster")
    axes[1, 1].set_ylabel("Number of Customers")
    axes[1, 1].set_title("Customer Distribution by Cluster")
    axes[1, 1].set_xticks(range(len(cluster_counts)))

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    buffer.seek(0)
    plot_data = buffer.getvalue()
    buffer.close()
    plt.close()

    return base64.b64encode(plot_data).decode()


def analyze_clusters(df: pd.DataFrame, clusters: np.ndarray) -> Dict[str, Any]:

    df_analysis = df.copy()
    df_analysis["cluster"] = clusters

    cluster_analysis = {}

    for cluster_id in sorted(df_analysis["cluster"].unique()):
        cluster_data = df_analysis[df_analysis["cluster"] == cluster_id]

        analysis = {
            "size": len(cluster_data),
            "percentage": (len(cluster_data) / len(df_analysis)) * 100,
            "avg_total_orders": cluster_data["total_orders"].mean(),
            "avg_total_quantity": cluster_data["total_quantity"].mean(),
            "avg_order_quantity": cluster_data["avg_order_quantity"].mean(),
            "avg_days_since_last": cluster_data["days_since_last_order"].mean(),
            "avg_order_frequency": cluster_data["order_frequency"].mean(),
            "avg_category_diversity": cluster_data["category_diversity"].mean(),
            "top_categories": {
                "chicken": cluster_data["chicken_ratio"].mean(),
                "beef": cluster_data["beef_ratio"].mean(),
                "veal": cluster_data["veal_ratio"].mean(),
                "lamb": cluster_data["lamb_ratio"].mean(),
                "other": cluster_data["other_ratio"].mean(),
            },
        }

        if analysis["avg_order_frequency"] > df_analysis["order_frequency"].quantile(
            0.75
        ):
            if analysis["avg_total_quantity"] > df_analysis["total_quantity"].quantile(
                0.75
            ):
                cluster_type = "VIP Customers"
                description = (
                    "High frequency, high volume customers - your most valuable segment"
                )
            else:
                cluster_type = "Frequent Small Buyers"
                description = "Regular customers with smaller orders - good for consistent revenue"
        elif analysis["avg_total_quantity"] > df_analysis["total_quantity"].quantile(
            0.75
        ):
            cluster_type = "Bulk Buyers"
            description = "Infrequent but large volume purchases - possibly B2B or special occasions"
        elif analysis["avg_days_since_last"] > df_analysis[
            "days_since_last_order"
        ].quantile(0.75):
            cluster_type = "At-Risk Customers"
            description = "Haven't ordered recently - need re-engagement campaigns"
        else:
            cluster_type = "Regular Customers"
            description = "Standard customer behavior - stable base"

        analysis["cluster_type"] = cluster_type
        analysis["description"] = description

        cluster_analysis[f"cluster_{cluster_id}"] = analysis

    return cluster_analysis
