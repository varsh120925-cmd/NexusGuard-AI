"""
NexusGuard Application Entry & FastAPI Orchestrator
Integrates REST APIs, Machine Learning Pipelines, Real-Time Open-Meteo Weather,
and Interactive Analytics Views.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
import app.models # Registers all SQLAlchemy models

# Import API Routers
from app.routes.auth_routes import router as auth_router
from app.routes.shipment_routes import router as shipment_router
from app.routes.prediction_routes import router as prediction_router
from app.routes.weather_routes import router as weather_router
from app.routes.anomaly_routes import router as anomaly_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.alert_routes import router as alert_router
from app.routes.report_routes import router as report_router
from app.routes.view_routes import router as view_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown

app = FastAPI(
    title="NexusGuard – AI Logistics Risk Prediction & Fraud Detection System",
    description="Intelligent logistics monitoring platform forecasting shipment risks, analyzing anomalies with Isolation Forest, and integrating live atmospheric Open-Meteo telemetry.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets
static_dir = settings.BASE_DIR / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount API Routers
app.include_router(auth_router)
app.include_router(shipment_router)
app.include_router(prediction_router)
app.include_router(weather_router)
app.include_router(anomaly_router)
app.include_router(dashboard_router)
app.include_router(alert_router)
app.include_router(report_router)

# Mount HTML View Routers
app.include_router(view_router)
