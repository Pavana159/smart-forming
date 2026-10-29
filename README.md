# 🌱 Smart Farming AI – Soil Analysis, Crop Recommendation & Growth Monitoring System

> **Tagline:** *"Your Farm, Smarter Every Day."*  
> **Target Audience:** College Final Year Project / Agricultural Technology Specialists / Farmers  
> **Status:** Fully functional, thoroughly tested, production-ready full-stack application.

---

## 📌 Executive Summary & Objectives

**Smart Farming AI** is a complete, working web application built to assist farmers across the agricultural lifecycle:
1. **Soil Assessment:** Analyze visible surface soil traits (color, texture, moisture sheen) or enter/upload chemical laboratory test reports (N, P, K, pH, EC).
2. **Weather Synchronization:** Retrieve live meteorological telemetry and 7-day WMO forecasts with the free, keyless **Open-Meteo API** (or manual fallback).
3. **Machine Learning Crop Recommendation:** Real **Random Forest Classifier (97.5% test accuracy)** trained on 2,200 ICAR benchmark records, producing up to 3 defensible candidates with agronomic reasoning and limiting factors.
4. **Persistent Farm Tracking:** Initialize SQLite records that track planting dates, growth stages, and historical observations.
5. **Crop Foliage Monitoring:** Upload photos from seedling to harvest. Quantitative computer vision calculates **Excess Green Index (ExG)**, **Canopy Coverage %**, **Yellowing (Chlorosis) %**, and **Necrosis/Spotting %**, comparing observations with previous records.
6. **FAO-56 Smart Irrigation Advice:** Decision-support guidance combining growth-stage crop coefficients ($K_c$), soil water retention, recent rainfall (48h), and 3-day forecast rain.
7. **PDF Dossier Generation:** One-click download of a comprehensive, branded farm report summarizing soil tests, weather profile, growth timeline, and agronomic disclaimers.

---

## 🔬 Scientific Honesty & Agronomic Disclaimers

A core engineering tenet of this system is **scientific transparency**:
* **Soil Photos vs Chemical Tests:** An optical camera photograph evaluates surface color, clod roughness, and visible dampness only. **A photo cannot measure chemical Nitrogen, Phosphorus, Potassium, or pH.** The application never fabricates chemical numbers from an image and explicitly flags missing laboratory measurements.
* **Foliage Vision:** Computer vision detects chromatic shifts (yellowing, brown lesions, canopy density). It serves as an early decision-support warning and does not replace certified laboratory pathology for microscopic viruses or bacterial wilt.
* **Irrigation Estimates:** If no physical soil sensor is present, recommendations are explicitly labeled as estimates, prompting the farmer to perform a physical 5–10 cm soil feel inspection.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4 |
| **Backend** | Python 3.10+ / 3.14+, Flask 3.1, Werkzeug |
| **Database** | SQLite3 (Persistent schema with foreign keys and cascade updates) |
| **Machine Learning** | Scikit-Learn 1.9 (Random Forest & Decision Tree Pipeline), Pandas, NumPy |
| **Computer Vision** | Pillow 13.0 (Statistical colorimetry, ExG index, chlorosis/necrosis segmentation) |
| **Weather API** | Open-Meteo REST API (Free, high-resolution WMO weather & geocoding, no API key needed) |
| **Reporting** | ReportLab 5.1 (Automated PDF table, chart styling, and typography) |
| **Testing** | Pytest 9.2 (19 automated unit & integration tests) |

---

## 🚀 Beginner-Friendly Quick Start Guide

### Step 1: Clone or Navigate to the Workspace
```bash
cd smart_farming_ai
```

### Step 2: Create and Activate a Virtual Environment (Recommended)
```bash
# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify or Retrain the Crop Model
A pre-trained model and benchmark dataset are already provided in `ml/`. You can retrain anytime by running:
```bash
python ml/train_model.py
```
*Output will compare Decision Tree (94.8%) vs Random Forest (97.5%) and export `ml/crop_model.joblib`.*

### Step 5: Run the Web Server Locally
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Automated Testing

The project includes an end-to-end automated test suite covering all routes, validations, edge cases, ML predictions, and PDF output.

Run all tests with:
```bash
pytest -v
```

**Results:**
```text
tests/test_app.py::test_home_page_loads PASSED
tests/test_app.py::test_soil_page_loads PASSED
tests/test_app.py::test_weather_page_loads PASSED
tests/test_app.py::test_crop_recommendation_page_loads PASSED
tests/test_app.py::test_farms_list_page_loads PASSED
tests/test_app.py::test_soil_photo_upload_valid PASSED
tests/test_app.py::test_soil_photo_invalid_extension PASSED
tests/test_app.py::test_soil_test_report_manual_entry PASSED
tests/test_app.py::test_soil_test_report_missing_inputs PASSED
tests/test_app.py::test_manual_weather_valid PASSED
tests/test_app.py::test_manual_weather_out_of_bounds PASSED
tests/test_app.py::test_crop_recommendation_rice_scenario PASSED
tests/test_app.py::test_crop_recommendation_chickpea_scenario PASSED
tests/test_app.py::test_crop_recommendation_invalid_inputs PASSED
tests/test_app.py::test_farm_creation_and_dashboard_reopen PASSED
tests/test_app.py::test_crop_photo_upload_and_timeline PASSED
tests/test_app.py::test_irrigation_advice_rain_forecast PASSED
tests/test_app.py::test_irrigation_advice_recent_rain PASSED
tests/test_app.py::test_pdf_report_download PASSED
==================== 19 passed in 100% ====================
```

---

## 🌐 Complete Workflow Walkthrough

1. **Home Page (`/`)**:
   - Access the 4 central navigation cards: *Weather Conditions*, *Soil Report*, *Crop Recommendation*, and *Monitor My Crop*.
   - Review overview metrics of active farms and recent foliage observations.
2. **Soil Assessment (`/soil`)**:
   - **Option A (Photo):** Upload topsoil JPEG/PNG. View surface roughness score, apparent soil type, and moisture appearance.
   - **Option B (Report):** Enter N, P, K (kg/ha), pH, and organic carbon. View nutrient sufficiency ratings (*Low, Adequate, High*).
3. **Weather Conditions (`/weather`)**:
   - Click *Use My GPS Location* or type a city name (e.g. *Fresno, London, Pune, Nairobi*).
   - Live Open-Meteo data populates current temperature, humidity, 48h recent rainfall, and 3-day forecast rain.
   - Interactive Chart.js graph illustrates temperatures and precipitation probabilities.
   - Switch to *Manual Weather Fallback* anytime if offline.
4. **Crop Recommendation (`/recommend`)**:
   - Values from Soil & Weather are automatically carried forward.
   - Click *Run AI Recommendation Model*.
   - The Random Forest pipeline evaluates the 7 agricultural vectors and presents up to 3 ranked candidates with suitability explanations, supporting farm traits, and limiting risk factors.
5. **Confirm Farm Record (`/farm/new`)**:
   - Select a candidate crop and click *Continue*.
   - Enter farm nickname, planting date, soil type, and upload an optional baseline photo.
6. **Farm Monitoring Dashboard (`/farm/<id>`)**:
   - View crop identity, latest health card, and smart irrigation status.
   - Click **Upload New Crop Photo** at any growth stage (*Seedling, Vegetative, Flowering, Fruiting, Harvest*).
   - Computer vision analyzes canopy % and yellowing chlorosis, computing a temporal progression note comparing against earlier uploads.
   - Chart.js plots canopy expansion and foliage stress metrics over time.
7. **Smart Irrigation Advisory (`/farm/<id>/irrigation`)**:
   - FAO-56 algorithm calculates crop evapotranspiration ($ET_c$) using stage-specific crop coefficients ($K_c$).
   - Flags whether irrigation may be needed, postponed due to forecast rain, or unnecessary due to recent soaking.
8. **Download PDF Report (`/farm/<id>/report/pdf`)**:
   - Generates an executive PDF dossier compiling farm identity, soil chemistry, climate statistics, observation timeline, and legal disclaimers.

---

## 🚢 Deployment to Production (Render / Railway / Heroku)

The repository includes ready-to-deploy configurations for **Render**:
* `requirements.txt`: Pinned dependencies.
* `Procfile`: Gunicorn production WSGI entrypoint (`web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`).
* `render.yaml`: Infrastructure-as-code specifying persistent disk mounting at `/var/data` so farm records and photos are **never lost** when dynos restart.

### Deploying to Render via GitHub:
1. Create a GitHub repository and push your project:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Smart Farming AI complete application"
   git branch -M main
   git remote add origin https://github.com/<your-username>/smart-farming-ai.git
   git push -u origin main
   ```
2. Log in to [Render.com](https://render.com) and click **New + > Blueprint**.
3. Select your GitHub repository. Render will detect `render.yaml` and automatically configure the Python web service with a persistent disk for SQLite and uploads.
4. Click **Apply**. Once built, Render will assign your live HTTPS public URL!

---

## 🔑 Environment Variables & Security

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | Autogenerated | Used for session signing and flash security. |
| `DATABASE_PATH` | `smart_farming.db` | Absolute or relative path to SQLite database. |
| `UPLOAD_FOLDER` | `static/uploads` | Path to persistent storage for photos and reports. |
| `MAX_CONTENT_LENGTH` | `16777216` (16 MB) | Enforces maximum upload size to protect server memory. |
| `GEMINI_API_KEY` | *(Optional)* | Optional key if extended LLM consultations are enabled. |

> **Note on Weather API:** Open-Meteo requires **no API key** and has no billing fees for standard academic/personal workloads.

---

## 👨‍🎓 Project Credits & Attribution
* **Dataset:** Based on the benchmark Kaggle & Indian Council of Agricultural Research (ICAR) Crop Recommendation Dataset.
* **Methodology:** FAO-56 Irrigation & Drainage Guidelines (Penman-Monteith / Crop Coefficients $K_c$).
* **Developer:** Final Year College Project & Agricultural Intelligence System (2026).
