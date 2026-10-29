"""
Smart Farming AI - Main Flask Application.
Complete Full-Stack Application for Soil Analysis, Crop Recommendation,
Growth Monitoring, and Irrigation Advisory.
"""
import os
import io
import json
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    flash, send_file, send_from_directory, abort, session
)
from werkzeug.utils import secure_filename

from config import Config
import database
from services.weather_service import get_live_weather, search_location, format_manual_weather
from services.soil_analysis_service import analyze_soil_image, parse_manual_soil_report, extract_text_from_report_file
from services.crop_recommendation_service import recommend_crops, get_or_load_model
from services.image_analysis_service import analyze_crop_image, ALLOWED_STAGES
from services.irrigation_service import evaluate_irrigation_need
from services.report_service import generate_farm_pdf_report

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload directories exist safely
for subdir in ['soil', 'crops', 'reports']:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], subdir), exist_ok=True)

# Initialize database schema
database.init_db()

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file_storage, folder_subdir, allowed_extensions):
    if not file_storage or file_storage.filename == '':
        return None, "No file selected."
    if not allowed_file(file_storage.filename, allowed_extensions):
        ext_list = ", ".join(allowed_extensions)
        return None, f"Invalid file type. Allowed formats: {ext_list}."
    
    orig_ext = file_storage.filename.rsplit('.', 1)[1].lower()
    # Randomized unique filename prevents path traversal and collisions
    safe_name = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}.{orig_ext}"
    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], folder_subdir)
    os.makedirs(target_dir, exist_ok=True)
    full_path = os.path.join(target_dir, safe_name)
    file_storage.save(full_path)
    # Return relative web path and absolute system path
    rel_path = f"uploads/{folder_subdir}/{safe_name}"
    return rel_path, full_path

# ---------------------------------------------------------
# Web Routes
# ---------------------------------------------------------

@app.route('/')
def index():
    """
    Home page: Website name, tagline, 4 main action buttons,
    summary of saved farms and recent monitoring records.
    """
    summary = database.get_dashboard_summary()
    notifications = database.get_notifications(limit=5)
    return render_template('index.html', summary=summary, notifications=notifications)

# ---------------------------------------------------------
# Soil Report Feature
# ---------------------------------------------------------

@app.route('/soil')
def soil_report():
    """
    Dedicated soil page with two clearly separated options:
    A. Upload Soil Photo (visual traits only, strict disclaimer)
    B. Enter or Upload Soil Test Report (chemical lab values)
    """
    return render_template('soil_report.html')

@app.route('/api/soil/photo', methods=['POST'])
def api_soil_photo():
    """
    Upload and analyze soil photo.
    Analyzes visual attributes only. Never fabricates NPK or pH.
    """
    if 'soil_photo' not in request.files:
        return jsonify({'success': False, 'error': 'No soil photo uploaded.'}), 400
    
    file = request.files['soil_photo']
    rel_path, abs_path = save_uploaded_file(file, 'soil', app.config['ALLOWED_IMAGE_EXTENSIONS'])
    if not rel_path:
        return jsonify({'success': False, 'error': abs_path}), 400
        
    analysis = analyze_soil_image(abs_path)
    if not analysis.get('success'):
        return jsonify(analysis), 400
        
    # Save record in database
    report_id = database.save_soil_report({
        'report_type': 'image',
        'file_path': rel_path,
        'soil_texture': analysis['visual_observations'].get('apparent_soil_type', 'Loamy'),
        'visible_observations': analysis['visual_observations'],
        'missing_measurements': analysis['missing_measurements'],
        'assessment_summary': analysis['assessment_summary']
    })
    
    return jsonify({
        'success': True,
        'report_id': report_id,
        'file_path': rel_path,
        'analysis': analysis
    })

@app.route('/api/soil/report', methods=['POST'])
def api_soil_report():
    """
    Processes laboratory soil test report: manual entry or optional file extraction.
    """
    rel_path = ''
    extracted_data = {}
    
    # Check if a report file was uploaded
    if 'report_file' in request.files and request.files['report_file'].filename != '':
        file = request.files['report_file']
        rel_path, abs_path = save_uploaded_file(file, 'reports', app.config['ALLOWED_REPORT_EXTENSIONS'])
        if not rel_path:
            return jsonify({'success': False, 'error': abs_path}), 400
        ext_res = extract_text_from_report_file(abs_path)
        if ext_res.get('success'):
            extracted_data = ext_res.get('extracted_fields', {})

    # Combine manual form fields with extracted fallback
    n = request.form.get('nitrogen') or extracted_data.get('nitrogen')
    p = request.form.get('phosphorus') or extracted_data.get('phosphorus')
    k = request.form.get('potassium') or extracted_data.get('potassium')
    ph = request.form.get('ph') or extracted_data.get('ph')
    oc = request.form.get('organic_carbon') or extracted_data.get('organic_carbon')
    ec = request.form.get('electrical_conductivity') or extracted_data.get('electrical_conductivity')
    soil_texture = request.form.get('soil_texture', 'Loamy')

    parsed = parse_manual_soil_report({
        'nitrogen': n,
        'phosphorus': p,
        'potassium': k,
        'ph': ph,
        'organic_carbon': oc,
        'electrical_conductivity': ec,
        'soil_texture': soil_texture
    })

    if not parsed.get('success'):
        return jsonify(parsed), 400

    report_id = database.save_soil_report({
        'report_type': 'test_report',
        'file_path': rel_path,
        'nitrogen': float(n) if n else None,
        'phosphorus': float(p) if p else None,
        'potassium': float(k) if k else None,
        'ph': float(ph) if ph else None,
        'organic_carbon': float(oc) if oc else None,
        'electrical_conductivity': float(ec) if ec else None,
        'soil_texture': soil_texture,
        'visible_observations': {},
        'missing_measurements': parsed['missing_measurements'],
        'assessment_summary': parsed['assessment_summary']
    })

    return jsonify({
        'success': True,
        'report_id': report_id,
        'file_path': rel_path,
        'analysis': parsed
    })

@app.route('/soil/result/<int:report_id>')
def soil_result(report_id):
    """
    Renders the structured soil assessment summary with next-step prompts.
    """
    report = database.get_soil_report_by_id(report_id)
    if not report:
        flash("Soil report not found.", "danger")
        return redirect(url_for('soil_report'))
    return render_template('soil_result.html', report=report)

# ---------------------------------------------------------
# Weather Conditions Feature
# ---------------------------------------------------------

@app.route('/weather')
def weather():
    """
    Weather page supporting browser geolocation, location search,
    live Open-Meteo conditions, 7-day forecast, and manual fallback.
    """
    return render_template('weather.html')

@app.route('/api/weather/live')
def api_weather_live():
    """
    Returns live weather JSON for specified lat/lon or city query.
    """
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    city = request.args.get('city')

    if city and (not lat or not lon):
        search_res = search_location(city)
        if not search_res.get('success') or not search_res.get('locations'):
            return jsonify(search_res), 400
        first_loc = search_res['locations'][0]
        lat = first_loc['latitude']
        lon = first_loc['longitude']
        location_name = first_loc['display_name']
    else:
        location_name = request.args.get('location_name', f"Field ({round(float(lat), 2)}, {round(float(lon), 2)})" if lat and lon else "Farm Location")

    if not lat or not lon:
        return jsonify({'success': False, 'error': 'Latitude and longitude coordinates are required.'}), 400

    weather_data = get_live_weather(lat, lon, location_name)
    if not weather_data.get('success'):
        return jsonify(weather_data), 400
    return jsonify(weather_data)

@app.route('/api/weather/search')
def api_weather_search():
    query = request.args.get('q', '')
    res = search_location(query)
    return jsonify(res)

@app.route('/api/weather/manual', methods=['POST'])
def api_weather_manual():
    temp = request.form.get('temperature')
    hum = request.form.get('humidity')
    rain = request.form.get('rainfall')
    loc = request.form.get('location_name', 'Manual Weather Station')

    res = format_manual_weather(temp, hum, rain, loc)
    if not res.get('success'):
        return jsonify(res), 400
    return jsonify(res)

# ---------------------------------------------------------
# Crop Recommendation Feature
# ---------------------------------------------------------

@app.route('/recommend')
def crop_recommendation():
    """
    Crop recommendation form combining soil and weather measurements.
    Pre-fills values from query parameters if coming from Soil Report or Weather.
    """
    prefill = {
        'n': request.args.get('n', ''),
        'p': request.args.get('p', ''),
        'k': request.args.get('k', ''),
        'ph': request.args.get('ph', ''),
        'temp': request.args.get('temp', ''),
        'humidity': request.args.get('humidity', ''),
        'rainfall': request.args.get('rainfall', ''),
        'location': request.args.get('location', ''),
        'soil_type': request.args.get('soil_type', 'Loamy'),
        'soil_report_ref': request.args.get('report_id', '')
    }
    return render_template('crop_recommendation.html', prefill=prefill)

@app.route('/api/recommend', methods=['POST'])
def api_recommend():
    """
    Validates inputs and predicts suitable crops using the saved Scikit-Learn pipeline.
    Returns up to 3 candidates with probability scores, reasoning, and limitations.
    """
    input_data = {
        'nitrogen': request.form.get('nitrogen'),
        'phosphorus': request.form.get('phosphorus'),
        'potassium': request.form.get('potassium'),
        'temperature': request.form.get('temperature'),
        'humidity': request.form.get('humidity'),
        'ph': request.form.get('ph'),
        'rainfall': request.form.get('rainfall'),
        'soil_type': request.form.get('soil_type', 'Loamy'),
        'location': request.form.get('location', 'General Field')
    }

    result = recommend_crops(input_data)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)

# ---------------------------------------------------------
# Farm Records & Continue Workflow
# ---------------------------------------------------------

@app.route('/farm/new')
def farm_new():
    """
    Page to confirm selected crop and initialize a farm monitoring record.
    """
    selected_crop = request.args.get('crop', '')
    if not selected_crop:
        flash("Please select a crop candidate first.", "warning")
        return redirect(url_for('crop_recommendation'))

    init_data = {
        'crop_selected': selected_crop,
        'location': request.args.get('location', ''),
        'soil_type': request.args.get('soil_type', 'Loamy'),
        'soil_report_ref': request.args.get('soil_report_ref', ''),
        'weather_summary': request.args.get('weather_summary', '')
    }
    return render_template('create_farm.html', init_data=init_data)

@app.route('/farm/create', methods=['POST'])
def farm_create():
    """
    Saves a persistent farm monitoring record in SQLite.
    """
    farm_name = request.form.get('farm_name', 'My Farm').strip()
    crop_selected = request.form.get('crop_selected', '').strip()
    planting_date = request.form.get('planting_date', datetime.now().strftime('%Y-%m-%d'))
    location = request.form.get('location', 'Main Field').strip()
    soil_type = request.form.get('soil_type', 'Loamy')
    soil_report_ref = request.form.get('soil_report_ref', '')
    weather_summary = request.form.get('weather_summary', '')
    stage = request.form.get('current_growth_stage', 'Immediately after planting')

    if not crop_selected:
        flash("Crop selection is required.", "danger")
        return redirect(url_for('crop_recommendation'))

    # Initial crop photo (optional)
    initial_photo_path = ''
    if 'initial_photo' in request.files and request.files['initial_photo'].filename != '':
        rel_p, abs_p = save_uploaded_file(request.files['initial_photo'], 'crops', app.config['ALLOWED_IMAGE_EXTENSIONS'])
        if rel_p:
            initial_photo_path = rel_p

    farm_id = database.create_farm({
        'farm_name': farm_name or f"{crop_selected} Field",
        'crop_selected': crop_selected,
        'planting_date': planting_date,
        'location': location,
        'soil_type': soil_type,
        'soil_report_ref': soil_report_ref,
        'initial_weather_summary': weather_summary,
        'initial_crop_photo': initial_photo_path,
        'current_growth_stage': stage
    })

    # If an initial photo was uploaded, record it as the first baseline observation
    if initial_photo_path:
        abs_path = os.path.join(app.root_path, 'static', initial_photo_path)
        c_res = analyze_crop_image(abs_path, crop_name=crop_selected, growth_stage=stage, previous_record=None)
        if c_res.get('success'):
            database.add_crop_monitoring_record({
                'farm_id': farm_id,
                'observation_date': planting_date,
                'growth_stage': stage,
                'photo_path': initial_photo_path,
                'greenness_index': c_res['greenness_index'],
                'chlorosis_yellowing': c_res['chlorosis_yellowing'],
                'necrosis_spots': c_res['necrosis_spots'],
                'canopy_coverage': c_res['canopy_coverage'],
                'health_status': c_res['health_status'],
                'visible_symptoms': c_res['visible_symptoms'],
                'comparison_notes': c_res['comparison_notes'],
                'farmer_notes': 'Initial baseline observation recorded at farm creation.',
                'confidence_score': c_res['confidence_score'],
                'limitations_disclaimer': c_res['limitations_disclaimer']
            })

    flash(f"Farm monitoring record successfully created for {crop_selected}!", "success")
    return redirect(url_for('farm_dashboard', farm_id=farm_id))

@app.route('/farms')
def farms_list():
    """
    Lists and reopens all saved farm monitoring records.
    """
    farms = database.get_all_farms()
    return render_template('farms_list.html', farms=farms)

@app.route('/farm/<int:farm_id>')
def farm_dashboard(farm_id):
    """
    Complete farm monitoring dashboard:
    - Farm identity and stage
    - Observation timeline
    - Latest photo and health analysis
    - Irrigation status card
    - Canopy and greenness progress chart
    - Button to 'Upload New Crop Photo'
    - Download PDF farm report
    """
    farm = database.get_farm_by_id(farm_id)
    if not farm:
        flash("Farm record not found.", "danger")
        return redirect(url_for('farms_list'))

    history = database.get_crop_monitoring_history(farm_id)
    latest_record = database.get_latest_crop_monitoring_record(farm_id)
    latest_irrigation = database.get_latest_irrigation_advice(farm_id)
    notifications = database.get_notifications(farm_id=farm_id, limit=5)

    # Fetch associated soil report if referenced
    soil_rep = None
    if farm.get('soil_report_ref') and str(farm['soil_report_ref']).isdigit():
        soil_rep = database.get_soil_report_by_id(int(farm['soil_report_ref']))

    return render_template(
        'farm_dashboard.html',
        farm=farm,
        history=history,
        latest_record=latest_record,
        latest_irrigation=latest_irrigation,
        notifications=notifications,
        soil_report=soil_rep,
        stages=ALLOWED_STAGES
    )

# ---------------------------------------------------------
# Crop Photo Upload & Growth Monitoring
# ---------------------------------------------------------

@app.route('/api/farm/<int:farm_id>/monitoring/upload', methods=['POST'])
def api_crop_photo_upload(farm_id):
    """
    Handles upload of new growth monitoring photo.
    Validates file, analyzes visible foliage, compares against previous observations,
    and appends to the immutable timeline.
    """
    farm = database.get_farm_by_id(farm_id)
    if not farm:
        return jsonify({'success': False, 'error': 'Farm record not found.'}), 404

    if 'crop_photo' not in request.files:
        return jsonify({'success': False, 'error': 'No image file uploaded.'}), 400

    file = request.files['crop_photo']
    rel_path, abs_path = save_uploaded_file(file, 'crops', app.config['ALLOWED_IMAGE_EXTENSIONS'])
    if not rel_path:
        return jsonify({'success': False, 'error': abs_path}), 400

    stage = request.form.get('growth_stage', farm.get('current_growth_stage', 'Vegetative growth'))
    obs_date = request.form.get('observation_date', datetime.now().strftime('%Y-%m-%d'))
    farmer_notes = request.form.get('farmer_notes', '').strip()

    # Retrieve previous record for temporal comparison
    prev_record = database.get_latest_crop_monitoring_record(farm_id)

    # Perform Computer Vision Foliage Analysis
    c_res = analyze_crop_image(abs_path, crop_name=farm['crop_selected'], growth_stage=stage, previous_record=prev_record)
    if not c_res.get('success'):
        return jsonify(c_res), 400

    # Save to database
    record_id = database.add_crop_monitoring_record({
        'farm_id': farm_id,
        'observation_date': obs_date,
        'growth_stage': stage,
        'photo_path': rel_path,
        'greenness_index': c_res['greenness_index'],
        'chlorosis_yellowing': c_res['chlorosis_yellowing'],
        'necrosis_spots': c_res['necrosis_spots'],
        'canopy_coverage': c_res['canopy_coverage'],
        'health_status': c_res['health_status'],
        'visible_symptoms': c_res['visible_symptoms'],
        'comparison_notes': c_res['comparison_notes'],
        'farmer_notes': farmer_notes,
        'confidence_score': c_res['confidence_score'],
        'limitations_disclaimer': c_res['limitations_disclaimer']
    })

    return jsonify({
        'success': True,
        'record_id': record_id,
        'photo_path': rel_path,
        'analysis': c_res
    })

# ---------------------------------------------------------
# Smart Irrigation & Water Requirement Advice
# ---------------------------------------------------------

@app.route('/farm/<int:farm_id>/irrigation')
def farm_irrigation_page(farm_id):
    """
    Dedicated Irrigation Advice page for a farm.
    """
    farm = database.get_farm_by_id(farm_id)
    if not farm:
        flash("Farm not found.", "danger")
        return redirect(url_for('farms_list'))

    latest_irrigation = database.get_latest_irrigation_advice(farm_id)
    return render_template('irrigation_advice.html', farm=farm, latest=latest_irrigation)

@app.route('/api/farm/<int:farm_id>/irrigation/assess', methods=['POST'])
def api_irrigation_assess(farm_id):
    """
    Evaluates irrigation status using FAO-56 crop coefficients, weather, soil type,
    and optional measured soil moisture sensor.
    """
    farm = database.get_farm_by_id(farm_id)
    if not farm:
        return jsonify({'success': False, 'error': 'Farm record not found.'}), 404

    growth_stage = request.form.get('growth_stage', farm.get('current_growth_stage', 'Vegetative growth'))
    soil_type = request.form.get('soil_type', farm.get('soil_type', 'Loamy'))
    soil_moisture = request.form.get('soil_moisture')

    # Weather metrics
    temp = request.form.get('temperature')
    hum = request.form.get('humidity')
    rec_rain = request.form.get('recent_rain_48h')
    fore_rain = request.form.get('forecast_rain_next_3days')

    # Build weather structure
    weather_payload = {
        'success': True,
        'temperature': float(temp) if temp else 26.0,
        'humidity': float(hum) if hum else 60.0,
        'recent_rain_48h': float(rec_rain) if rec_rain else 0.0,
        'forecast_rain_next_3days': float(fore_rain) if fore_rain else 0.0
    }

    advice = evaluate_irrigation_need(
        crop_name=farm['crop_selected'],
        growth_stage=growth_stage,
        weather_data=weather_payload,
        soil_type=soil_type,
        soil_moisture=soil_moisture
    )

    if advice.get('success'):
        database.save_irrigation_advice({
            'farm_id': farm_id,
            'status': advice['status'],
            'crop_stage': growth_stage,
            'soil_moisture_measured': float(soil_moisture) if soil_moisture and str(soil_moisture).strip() != '' else None,
            'forecast_rain_mm': advice['forecast_rain_mm'],
            'recent_rain_mm': advice['recent_rain_mm'],
            'temperature': advice['temperature'],
            'et0_estimate': advice['et0_estimate'],
            'crop_coefficient_kc': advice['crop_coefficient_kc'],
            'recommended_action': advice['recommended_action'],
            'detailed_reasons': advice['detailed_reasons'],
            'next_check_time': advice['next_check_time'],
            'is_sensor_available': advice['is_sensor_available']
        })

    return jsonify(advice)

# ---------------------------------------------------------
# PDF Dossier Report Download
# ---------------------------------------------------------

@app.route('/farm/<int:farm_id>/report/pdf')
def farm_pdf_report(farm_id):
    """
    Generates and downloads a complete farm monitoring dossier in PDF format.
    """
    farm = database.get_farm_by_id(farm_id)
    if not farm:
        abort(404, description="Farm record not found.")

    history = database.get_crop_monitoring_history(farm_id)
    latest_irrigation = database.get_latest_irrigation_advice(farm_id)
    
    soil_rep = None
    if farm.get('soil_report_ref') and str(farm['soil_report_ref']).isdigit():
        soil_rep = database.get_soil_report_by_id(int(farm['soil_report_ref']))

    pdf_bytes = generate_farm_pdf_report(
        farm_data=farm,
        soil_report=soil_rep,
        latest_weather={'success': True, 'temperature': 25, 'humidity': 60, 'recent_rain_48h': 0, 'forecast_rain_next_3days': 5, 'condition': 'Partly cloudy'},
        monitoring_records=history,
        irrigation_advice=latest_irrigation
    )

    filename = f"{secure_filename(farm['farm_name'])}_{farm['crop_selected']}_Report.pdf"
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# ---------------------------------------------------------
# Notifications API
# ---------------------------------------------------------

@app.route('/api/notifications')
def api_get_notifications():
    farm_id = request.args.get('farm_id')
    notifs = database.get_notifications(farm_id=int(farm_id) if farm_id else None)
    return jsonify({'success': True, 'notifications': notifs})

if __name__ == '__main__':
    # Beginner friendly local development launcher
    print("\n" + "="*60)
    print(" SMART FARMING AI - Soil Analysis, Crop Recommendation & Monitoring")
    print(" Server running locally at: http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
