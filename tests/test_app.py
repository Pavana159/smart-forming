"""
Automated Test Suite for Smart Farming AI Web Application.
Tests routes, image analysis, model inference, database persistence,
validation constraints, weather fallback, irrigation logic, and PDF generation.
"""
import os
import sys
import io
import pytest
from PIL import Image

# Ensure app modules are in sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(TEST_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import app
import database

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Use isolated test database
    app.config['DATABASE_PATH'] = os.path.join(APP_DIR, 'test_smart_farming.db')
    database.init_db()
    with app.test_client() as client:
        yield client
    # Clean up test database
    if os.path.exists(app.config['DATABASE_PATH']):
        try:
            os.remove(app.config['DATABASE_PATH'])
        except Exception:
            pass

def create_dummy_image(format='PNG', size=(100, 100), color=(34, 139, 34)):
    """Helper to generate in-memory dummy image file."""
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf

# -------------------------------------------------------------
# 1. Main Route & Navigation Tests
# -------------------------------------------------------------

def test_home_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Smart Farming AI" in html
    assert "Your Farm, Smarter Every Day." in html
    assert "Soil Report" in html
    assert "Weather Conditions" in html
    assert "Crop Recommendation" in html
    assert "Monitor My Crop" in html

def test_soil_page_loads(client):
    response = client.get('/soil')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Option A: Upload Soil Photo" in html
    assert "Option B: Soil Test Report" in html
    assert "Scientific Integrity Principle" in html

def test_weather_page_loads(client):
    response = client.get('/weather')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Farm Weather Conditions & Forecast" in html
    assert "Manual Weather Fallback" in html

def test_crop_recommendation_page_loads(client):
    response = client.get('/recommend')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "AI Crop Recommendation Engine" in html

def test_farms_list_page_loads(client):
    response = client.get('/farms')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "My Farm Monitoring Records" in html

# -------------------------------------------------------------
# 2. Soil Photo & Report Validation Tests
# -------------------------------------------------------------

def test_soil_photo_upload_valid(client):
    img_buf = create_dummy_image(format='JPEG', color=(101, 67, 33)) # Dark brown soil
    data = {'soil_photo': (img_buf, 'test_soil.jpg')}
    response = client.post('/api/soil/photo', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'report_id' in json_data
    # Verify scientific principle: optical photo lists missing chemical nutrients
    missing = json_data['analysis']['missing_measurements']
    assert any(m['field'] == 'Nitrogen (N)' for m in missing)
    assert any(m['field'] == 'Soil pH' for m in missing)

def test_soil_photo_invalid_extension(client):
    data = {'soil_photo': (io.BytesIO(b"fake text"), 'malicious.exe')}
    response = client.post('/api/soil/photo', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Invalid file type" in json_data['error']

def test_soil_test_report_manual_entry(client):
    data = {
        'nitrogen': '240',
        'phosphorus': '35',
        'potassium': '180',
        'ph': '6.8',
        'soil_texture': 'Loamy'
    }
    response = client.post('/api/soil/report', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    analysis = json_data['analysis']
    assert analysis['measurements']['nitrogen']['rating'] == 'Low'
    assert analysis['measurements']['ph']['rating'] == 'Near Neutral (Ideal)'

def test_soil_test_report_missing_inputs(client):
    data = {'soil_texture': 'Sandy'} # No N, P, K, pH provided
    response = client.post('/api/soil/report', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    analysis = json_data['analysis']
    assert len(analysis['missing_measurements']) == 4

# -------------------------------------------------------------
# 3. Weather Service & Manual Fallback Tests
# -------------------------------------------------------------

def test_manual_weather_valid(client):
    data = {
        'temperature': '27.5',
        'humidity': '72.0',
        'rainfall': '45.0',
        'location_name': 'Test Farm'
    }
    response = client.post('/api/weather/manual', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['temperature'] == 27.5
    assert json_data['is_manual'] is True

def test_manual_weather_out_of_bounds(client):
    data = {
        'temperature': '120.0', # Unrealistic temp
        'humidity': '50.0',
        'rainfall': '10.0'
    }
    response = client.post('/api/weather/manual', data=data)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Temperature must be between" in json_data['error']

# -------------------------------------------------------------
# 4. Machine Learning Crop Prediction Tests
# -------------------------------------------------------------

def test_crop_recommendation_rice_scenario(client):
    # Rice standard inputs: warm, high rainfall, high humidity, balanced NPK
    data = {
        'nitrogen': '85',
        'phosphorus': '48',
        'potassium': '40',
        'temperature': '24.0',
        'humidity': '82.0',
        'ph': '6.4',
        'rainfall': '230.0',
        'soil_type': 'Clay Loam'
    }
    response = client.post('/api/recommend', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    candidates = json_data['candidates']
    assert len(candidates) >= 1
    # Check top candidate
    top = candidates[0]
    assert 'Rice' in top['crop_name'] or 'Jute' in top['crop_name']
    assert 'why_suitable' in top
    assert len(top['supporting_conditions']) > 0

def test_crop_recommendation_chickpea_scenario(client):
    # Chickpea standard inputs: cool temp, very low humidity, high K
    data = {
        'nitrogen': '40',
        'phosphorus': '68',
        'potassium': '80',
        'temperature': '18.5',
        'humidity': '17.0',
        'ph': '7.2',
        'rainfall': '75.0'
    }
    response = client.post('/api/recommend', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    top = json_data['candidates'][0]
    assert 'Chickpea' in top['crop_name']

def test_crop_recommendation_invalid_inputs(client):
    data = {
        'nitrogen': '-50', # Negative N
        'phosphorus': '40',
        'potassium': '40',
        'temperature': '25',
        'humidity': '80',
        'ph': '6.5',
        'rainfall': '100'
    }
    response = client.post('/api/recommend', data=data)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "outside realistic agricultural bounds" in json_data['error']

# -------------------------------------------------------------
# 5. Farm Record Creation & Reopening Tests
# -------------------------------------------------------------

def test_farm_creation_and_dashboard_reopen(client):
    data = {
        'farm_name': 'Green Acres Test Plot',
        'crop_selected': 'Rice',
        'planting_date': '2026-05-15',
        'location': 'Northern Basin',
        'soil_type': 'Clay Loam',
        'current_growth_stage': 'Seedling growth'
    }
    response = client.post('/farm/create', data=data, follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert "Green Acres Test Plot" in html
    assert "Rice" in html
    assert "Seedling growth" in html

# -------------------------------------------------------------
# 6. Growth Monitoring Photo Upload & Timeline Tests
# -------------------------------------------------------------

def test_crop_photo_upload_and_timeline(client):
    # 1. Create a test farm
    farm_id = database.create_farm({
        'farm_name': 'Timeline Test Farm',
        'crop_selected': 'Maize',
        'planting_date': '2026-06-01',
        'current_growth_stage': 'Vegetative growth'
    })

    # 2. Upload growth photo (green foliage)
    img_buf = create_dummy_image(format='PNG', color=(34, 139, 34))
    upload_data = {
        'crop_photo': (img_buf, 'maize_veg.png'),
        'growth_stage': 'Vegetative growth',
        'observation_date': '2026-06-15',
        'farmer_notes': 'Canopy looking vigorous and green.'
    }
    res = client.post(f'/api/farm/{farm_id}/monitoring/upload', data=upload_data, content_type='multipart/form-data')
    assert res.status_code == 200
    res_json = res.get_json()
    assert res_json['success'] is True
    assert res_json['analysis']['canopy_coverage'] > 0

    # 3. Upload second photo (flowering) and verify history persists both
    img_buf2 = create_dummy_image(format='JPEG', color=(40, 160, 40))
    upload_data2 = {
        'crop_photo': (img_buf2, 'maize_flower.jpg'),
        'growth_stage': 'Flowering',
        'observation_date': '2026-07-01'
    }
    res2 = client.post(f'/api/farm/{farm_id}/monitoring/upload', data=upload_data2, content_type='multipart/form-data')
    assert res2.status_code == 200

    history = database.get_crop_monitoring_history(farm_id)
    assert len(history) == 2
    assert history[0]['growth_stage'] == 'Vegetative growth'
    assert history[1]['growth_stage'] == 'Flowering'

# -------------------------------------------------------------
# 7. Smart Irrigation Advisory Tests
# -------------------------------------------------------------

def test_irrigation_advice_rain_forecast(client):
    farm_id = database.create_farm({
        'farm_name': 'Irrigation Test Farm',
        'crop_selected': 'Cotton',
        'current_growth_stage': 'Vegetative growth'
    })
    # Imminent rain forecast (25mm)
    data = {
        'growth_stage': 'Vegetative growth',
        'soil_type': 'Loamy',
        'forecast_rain_next_3days': '25.0',
        'recent_rain_48h': '0.0',
        'temperature': '30.0',
        'humidity': '60.0'
    }
    res = client.post(f'/api/farm/{farm_id}/irrigation/assess', data=data)
    assert res.status_code == 200
    res_json = res.get_json()
    assert res_json['status'] == 'Check soil moisture before watering.'
    assert any("Rain is forecast soon" in r for r in res_json['detailed_reasons'])

def test_irrigation_advice_recent_rain(client):
    farm_id = database.create_farm({
        'farm_name': 'Rain Test Farm',
        'crop_selected': 'Wheat',
        'current_growth_stage': 'Seedling growth'
    })
    # Field received heavy rain (30mm) in past 48h
    data = {
        'growth_stage': 'Seedling growth',
        'soil_type': 'Clay',
        'recent_rain_48h': '30.0',
        'forecast_rain_next_3days': '0.0'
    }
    res = client.post(f'/api/farm/{farm_id}/irrigation/assess', data=data)
    assert res.status_code == 200
    res_json = res.get_json()
    assert res_json['status'] == 'Irrigation may not be needed yet.'

# -------------------------------------------------------------
# 8. PDF Farm Dossier Report Generation Test
# -------------------------------------------------------------

def test_pdf_report_download(client):
    farm_id = database.create_farm({
        'farm_name': 'PDF Test Plot',
        'crop_selected': 'Banana',
        'planting_date': '2026-03-01',
        'location': 'Tropical Sector'
    })
    response = client.get(f'/farm/{farm_id}/report/pdf')
    assert response.status_code == 200
    assert response.content_type == 'application/pdf'
    # Check standard PDF file signature (%PDF-)
    assert response.data.startswith(b'%PDF-')
