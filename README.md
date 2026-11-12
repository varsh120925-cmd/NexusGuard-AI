# NexusGuard: AI-Based Logistics Risk Prediction & Fraud Detection System

**NexusGuard** is an enterprise-grade logistics monitoring, risk prediction, and fraud detection platform. Designed for modern supply chain operations, NexusGuard evaluates multi-modal freight consignments, anticipates transit disruptions using Machine Learning, detects suspicious anomaly patterns with unsupervised Isolation Forests, and integrates real-time atmospheric data from the Open-Meteo API.

---

## Key Features

1. **Machine Learning Risk Prediction**:
   - Supervised classification trained on a high-fidelity logistics dataset (12,000+ multi-modal freight records across 20 international transport hubs).
   - Evaluates multiple classifiers: **Gradient Boosting Classifier**, **Random Forest Classifier**, **Decision Tree**, and **Logistic Regression**.
   - Generates probabilistic risk ratings and classifies consignments into **Low**, **Medium**, and **High Risk**.
   - Feature attribution breakdowns explaining exact factors influencing the prediction.

2. **Fraud & Anomaly Detection**:
   - Unsupervised **Isolation Forest** outlier detection combined with domain-specific freight security heuristics.
   - Detects abnormal declared values relative to cargo weight and category, incompatible transport mode/priority assignments, and irregular route deviations.
   - Flags entries as *"Suspicious Pattern Requiring Verification"* rather than prematurely asserting fraud, with a full investigator review workflow.

3. **Real-Time Atmospheric Weather Integration (Open-Meteo API)**:
   - Direct integration with Open-Meteo's live weather forecast and geocoding services.
   - Evaluates ambient temperature, precipitation intensity, and gale-force wind velocities for origin and destination terminals.
   - In-memory caching (15-minute TTL) for instantaneous subsequent queries and rate-limit preservation.
   - Resilient error handling: if the live API is unreachable, provides clear fallback status without generating fabricated numbers.

4. **Multi-Factor Risk Scoring Engine**:
   - Transparent composite formula (0 to 100):
     $$\text{Risk Score} = 0.45 \times P(\text{ML Delay}) + 0.20 \times \text{Weather Index} + 0.15 \times \text{Route Index} + 0.10 \times \text{Carrier Delay} + 0.10 \times \text{Anomaly Severity}$$
   - Clean risk categorization: Low Risk (0–39), Medium Risk (40–69), and High Risk (70–100).

5. **Executive PDF Report Generation**:
   - Automated compilation of downloadable compliance and audit PDF reports using ReportLab.
   - Includes official branding, risk score meter, shipment specifications, atmospheric telemetry, fraud pattern findings, and prescriptive AI recommendations.

6. **13 Fully Functional Interactive Dashboards**:
   - Modern Dark Navy Blue (`#0b1329`) and crisp white interface.
   - Interactive Chart.js charts for risk distributions, historical trends, transport mode comparisons, and weather tiers.
   - Filterable, searchable, and sortable shipment history tables.

---

## Machine Learning Architecture & Benchmark Results

The ML models were trained and benchmarked on a stratified 80/20 train/test split (9,600 training samples, 2,400 held-out test samples):

| Classifier Algorithm | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Production Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gradient Boosting Classifier** | **89.08%** | **87.04%** | **85.60%** | **0.8631** | **0.9589** | **Selected Optimal Model** |
| Random Forest Classifier | 88.00% | 86.91% | 82.59% | 0.8470 | 0.9516 | Evaluated |
| Logistic Regression | 88.92% | 86.67% | 85.60% | 0.8613 | 0.9602 | Evaluated |
| Decision Tree Classifier | 84.17% | 82.18% | 77.41% | 0.7972 | 0.9118 | Evaluated |

### Top Contributing Factors:
1. `carrier_historical_delay_rate` (0.384)
2. `weather_severity_index` (0.246)
3. `distance_km` (0.142)
4. `transit_stops` (0.088)
5. `val_weight_ratio` (0.065)

---

## Project Structure

```
nexusguard-new/
│
├── app/
│   ├── config.py                 # Application settings & environment configuration
│   ├── database.py               # SQLAlchemy SQLite engine and session factory
│   ├── main.py                   # FastAPI initialization & router mounting
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py               # User authentication model
│   │   ├── shipment.py           # Shipment consignment model
│   │   ├── prediction.py         # Risk prediction & score model
│   │   ├── weather.py            # Open-Meteo atmospheric observation model
│   │   ├── anomaly.py            # Fraud & outlier record model
│   │   ├── alert.py              # Operational risk notification model
│   │   └── report.py             # Generated PDF audit report model
│   ├── schemas/                  # Pydantic request/response validation schemas
│   ├── services/
│   │   ├── auth_service.py       # Bcrypt hashing & JWT token management
│   │   ├── weather_service.py    # Open-Meteo live API integration & caching
│   │   ├── risk_scoring_service.py # Multi-factor composite risk scoring engine
│   │   ├── recommendation_service.py # Prescriptive AI recommendation engine
│   │   └── report_service.py     # ReportLab executive PDF report generator
│   ├── ml/
│   │   ├── preprocessor.py       # Feature engineering & scaling pipelines
│   │   ├── model_trainer.py      # Multi-model training & evaluation script
│   │   └── predictor.py          # Unified inference & anomaly detection engine
│   ├── routes/                   # REST API and HTML View routers
│   ├── templates/                # Jinja2 HTML templates for all 13 pages
│   └── static/                   # Dark navy CSS and client-side JavaScript
│
├── dataset/
│   ├── generate_dataset.py       # Supply chain dataset generation script
│   ├── logistics_risk_dataset.csv# 12,000 consignment records
│   └── dataset_metadata.json     # Feature dictionary & statistical summary
│
├── trained_models/
│   ├── logistics_risk_rf_model.joblib # Saved Gradient Boosting classifier
│   ├── preprocessor.joblib       # Saved Scikit-Learn transformer pipeline
│   ├── isolation_forest_anomaly.joblib # Saved Isolation Forest anomaly detector
│   └── model_metrics.json        # Evaluation metrics & confusion matrix
│
├── reports/                      # Directory for compiled PDF shipment reports
├── scripts/
│   ├── seed_database.py          # Seeds database with demo records & compiles sample PDF
│   └── train_and_evaluate.py     # Retrains and benchmarks ML models
├── tests/                        # Automated Pytest integration test suite
├── run.py                        # Uvicorn server launcher
├── requirements.txt              # Production Python dependencies
├── .env.example                  # Environment template
├── .gitignore
└── README.md
```

---

## 13 Dashboard Pages

1. **Login & Registration** (`/login`): Authentication with bcrypt & JWT.
2. **Main Dashboard** (`/dashboard`): Real KPI cards, interactive Chart.js charts, and live recent activity.
3. **Shipment Registration** (`/shipments/new`): Enrollment form with geodesic distance calculator.
4. **Shipment Risk Prediction** (`/predictions/new`): Interactive prediction studio with risk gauge & factors.
5. **Live Weather Monitoring** (`/weather`): Real-time Open-Meteo radar and matrix across 20 international hubs.
6. **Route & Shipment Analysis** (`/routes`): Geographic corridor coordinates, waypoints & checkpoint breakdown.
7. **Fraud & Anomaly Detection** (`/fraud-detection`): Flagged outlier patterns with investigation review status.
8. **Risk Analytics** (`/analytics`): Model benchmark comparisons, test confusion matrix, and feature importances.
9. **Shipment History** (`/history`): Searchable, filterable, and sortable historical manifests with PDF download.
10. **Risk Alerts & Notifications** (`/alerts`): Critical risk warnings with mark-as-read workflow.
11. **AI Recommendations** (`/recommendations`): Prescriptive operational mitigation actions directory.
12. **Detailed Shipment Reports** (`/reports`): Report archive and on-demand PDF compilation.
13. **Settings & Profile** (`/settings`): Operator credentials, model status, and live API connectivity checks.

---

## Installation & Execution Instructions

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11).

### 2. Environment Setup
```bash
# Navigate to project directory
cd nexusguard-new

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python scripts/seed_database.py
```
*Creates the SQLite database (`nexusguard.db`), sets up default operator accounts, generates 12 demo shipments with live weather evaluation, and compiles a sample PDF report.*

### 4. Run the Application
```bash
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### Default Login Credentials:
- **Email**: `admin@nexusguard.io`
- **Password**: `admin123`
*(Alternative: `security@nexusguard.io` / `security123`)*

---

## Running Automated Tests

Run the full automated Pytest test suite:
```bash
pytest tests/ -v
```
All **17 test suites** verify:
- Bcrypt password hashing & JWT token issuance.
- ML data preprocessing & custom feature engineering (`LogisticsFeatureEngineer`).
- Machine Learning classification model inference & probability bounds.
- Isolation Forest outlier pattern detection & domain fraud heuristics.
- Live Open-Meteo API requests, geocoding resolution, and caching with TTL.
- Multi-factor risk engine calculations (0–100 score bounds).
- Actionable AI recommendation engine generation.
- REST API endpoints for shipments, predictions, dashboard KPIs, and anomalies.
- PDF report generation and download file integrity.
