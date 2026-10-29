"""
SQLite database layer for Smart Farming AI.
Provides clean persistent storage for farms, soil reports, monitoring records, and irrigation history.
Designed for easy migration to PostgreSQL/MySQL in production.
"""
import sqlite3
import os
import json
from datetime import datetime
from config import Config

def get_db_connection():
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Farms Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_name TEXT NOT NULL,
        crop_selected TEXT NOT NULL,
        variety TEXT DEFAULT '',
        planting_date TEXT NOT NULL,
        location TEXT DEFAULT '',
        latitude REAL,
        longitude REAL,
        soil_type TEXT DEFAULT 'Loamy',
        soil_report_ref TEXT DEFAULT '',
        initial_weather_summary TEXT DEFAULT '',
        initial_crop_photo TEXT DEFAULT '',
        current_growth_stage TEXT DEFAULT 'Seedling',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    
    # 2. Soil Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS soil_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        report_type TEXT NOT NULL, -- 'image' or 'test_report'
        file_path TEXT DEFAULT '',
        nitrogen REAL,
        phosphorus REAL,
        potassium REAL,
        ph REAL,
        organic_carbon REAL,
        electrical_conductivity REAL,
        soil_texture TEXT DEFAULT '',
        visible_observations TEXT DEFAULT '{}',
        missing_measurements TEXT DEFAULT '[]',
        assessment_summary TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
    );
    """)
    
    # 3. Crop Monitoring Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crop_monitoring_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER NOT NULL,
        observation_date TEXT NOT NULL,
        growth_stage TEXT NOT NULL,
        photo_path TEXT NOT NULL,
        greenness_index REAL DEFAULT 0.0,
        chlorosis_yellowing REAL DEFAULT 0.0,
        necrosis_spots REAL DEFAULT 0.0,
        canopy_coverage REAL DEFAULT 0.0,
        health_status TEXT NOT NULL,
        visible_symptoms TEXT DEFAULT '[]',
        comparison_notes TEXT DEFAULT '',
        farmer_notes TEXT DEFAULT '',
        confidence_score REAL DEFAULT 0.0,
        limitations_disclaimer TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
    );
    """)
    
    # 4. Irrigation Advice History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS irrigation_advice_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        crop_stage TEXT DEFAULT '',
        soil_moisture_measured REAL,
        forecast_rain_mm REAL DEFAULT 0.0,
        recent_rain_mm REAL DEFAULT 0.0,
        temperature REAL,
        et0_estimate REAL,
        crop_coefficient_kc REAL,
        recommended_action TEXT DEFAULT '',
        detailed_reasons TEXT DEFAULT '[]',
        next_check_time TEXT DEFAULT '',
        is_sensor_available INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
    );
    """)
    
    # 5. Dashboard Notifications Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

# Database Helper Functions
def create_farm(data):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO farms (
            farm_name, crop_selected, variety, planting_date, location,
            latitude, longitude, soil_type, soil_report_ref,
            initial_weather_summary, initial_crop_photo, current_growth_stage,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('farm_name', 'My Smart Farm'),
        data.get('crop_selected', 'Wheat'),
        data.get('variety', ''),
        data.get('planting_date', datetime.now().strftime('%Y-%m-%d')),
        data.get('location', 'Local Field'),
        data.get('latitude', None),
        data.get('longitude', None),
        data.get('soil_type', 'Loamy'),
        data.get('soil_report_ref', ''),
        data.get('initial_weather_summary', ''),
        data.get('initial_crop_photo', ''),
        data.get('current_growth_stage', 'Seedling'),
        now, now
    ))
    farm_id = cursor.lastrowid
    
    # Add initial welcome notification
    cursor.execute("""
        INSERT INTO notifications (farm_id, category, title, message, severity, created_at)
        VALUES (?, 'monitoring', 'Farm Monitoring Activated', ?, 'success', ?)
    """, (
        farm_id,
        f"Farm record created for {data.get('crop_selected')}. Upload new photos as your crop develops to track health.",
        now
    ))
    
    conn.commit()
    conn.close()
    return farm_id

def get_all_farms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farms ORDER BY id DESC")
    farms = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return farms

def get_farm_by_id(farm_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_farm_growth_stage(farm_id, new_stage):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "UPDATE farms SET current_growth_stage = ?, updated_at = ? WHERE id = ?",
        (new_stage, now, farm_id)
    )
    conn.commit()
    conn.close()

def save_soil_report(data):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO soil_reports (
            farm_id, report_type, file_path, nitrogen, phosphorus, potassium,
            ph, organic_carbon, electrical_conductivity, soil_texture,
            visible_observations, missing_measurements, assessment_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('farm_id'),
        data.get('report_type', 'test_report'),
        data.get('file_path', ''),
        data.get('nitrogen'),
        data.get('phosphorus'),
        data.get('potassium'),
        data.get('ph'),
        data.get('organic_carbon'),
        data.get('electrical_conductivity'),
        data.get('soil_texture', ''),
        json.dumps(data.get('visible_observations', {})),
        json.dumps(data.get('missing_measurements', [])),
        data.get('assessment_summary', ''),
        now
    ))
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id

def get_soil_reports(farm_id=None, limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    if farm_id:
        cursor.execute("SELECT * FROM soil_reports WHERE farm_id = ? ORDER BY id DESC LIMIT ?", (farm_id, limit))
    else:
        cursor.execute("SELECT * FROM soil_reports ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        r['visible_observations'] = json.loads(r['visible_observations'] or '{}')
        r['missing_measurements'] = json.loads(r['missing_measurements'] or '[]')
    return rows

def get_soil_report_by_id(report_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM soil_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        r = dict(row)
        r['visible_observations'] = json.loads(r['visible_observations'] or '{}')
        r['missing_measurements'] = json.loads(r['missing_measurements'] or '[]')
        return r
    return None

def add_crop_monitoring_record(data):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crop_monitoring_records (
            farm_id, observation_date, growth_stage, photo_path,
            greenness_index, chlorosis_yellowing, necrosis_spots, canopy_coverage,
            health_status, visible_symptoms, comparison_notes, farmer_notes,
            confidence_score, limitations_disclaimer, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('farm_id'),
        data.get('observation_date', datetime.now().strftime('%Y-%m-%d')),
        data.get('growth_stage', 'Vegetative'),
        data.get('photo_path'),
        data.get('greenness_index', 0.0),
        data.get('chlorosis_yellowing', 0.0),
        data.get('necrosis_spots', 0.0),
        data.get('canopy_coverage', 0.0),
        data.get('health_status', 'Healthy'),
        json.dumps(data.get('visible_symptoms', [])),
        data.get('comparison_notes', ''),
        data.get('farmer_notes', ''),
        data.get('confidence_score', 0.85),
        data.get('limitations_disclaimer', ''),
        now
    ))
    record_id = cursor.lastrowid
    
    # Update current growth stage on farm
    cursor.execute(
        "UPDATE farms SET current_growth_stage = ?, updated_at = ? WHERE id = ?",
        (data.get('growth_stage'), now, data.get('farm_id'))
    )
    
    # Notification if health stress detected
    if data.get('health_status') in ['Moderate Stress', 'Severe Stress', 'Uncertain']:
        cursor.execute("""
            INSERT INTO notifications (farm_id, category, title, message, severity, created_at)
            VALUES (?, 'inspection', 'Field Inspection Recommended', ?, 'warning', ?)
        """, (
            data.get('farm_id'),
            f"Observation on {data.get('growth_stage')} noted {data.get('health_status')}. Symptoms: {', '.join(data.get('visible_symptoms', [])) or 'Color irregularity'}.",
            now
        ))
        
    conn.commit()
    conn.close()
    return record_id

def get_crop_monitoring_history(farm_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM crop_monitoring_records WHERE farm_id = ? ORDER BY id ASC",
        (farm_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        r['visible_symptoms'] = json.loads(r['visible_symptoms'] or '[]')
    return rows

def get_latest_crop_monitoring_record(farm_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM crop_monitoring_records WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        r = dict(row)
        r['visible_symptoms'] = json.loads(r['visible_symptoms'] or '[]')
        return r
    return None

def save_irrigation_advice(data):
    conn = get_db_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO irrigation_advice_history (
            farm_id, status, crop_stage, soil_moisture_measured,
            forecast_rain_mm, recent_rain_mm, temperature, et0_estimate,
            crop_coefficient_kc, recommended_action, detailed_reasons,
            next_check_time, is_sensor_available, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('farm_id'),
        data.get('status'),
        data.get('crop_stage', ''),
        data.get('soil_moisture_measured'),
        data.get('forecast_rain_mm', 0.0),
        data.get('recent_rain_mm', 0.0),
        data.get('temperature'),
        data.get('et0_estimate'),
        data.get('crop_coefficient_kc'),
        data.get('recommended_action', ''),
        json.dumps(data.get('detailed_reasons', [])),
        data.get('next_check_time', ''),
        1 if data.get('is_sensor_available') else 0,
        now
    ))
    advice_id = cursor.lastrowid
    
    # Alert if irrigation needed or uncertain
    if data.get('status') == 'Irrigation may be needed':
        cursor.execute("""
            INSERT INTO notifications (farm_id, category, title, message, severity, created_at)
            VALUES (?, 'irrigation', 'Irrigation Assessment Alert', ?, 'info', ?)
        """, (
            data.get('farm_id'),
            f"Conditions suggest water requirement for {data.get('crop_stage')}. {data.get('recommended_action')}",
            now
        ))
    conn.commit()
    conn.close()
    return advice_id

def get_latest_irrigation_advice(farm_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM irrigation_advice_history WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        r = dict(row)
        r['detailed_reasons'] = json.loads(r['detailed_reasons'] or '[]')
        return r
    return None

def get_notifications(farm_id=None, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    if farm_id:
        cursor.execute("SELECT * FROM notifications WHERE farm_id = ? ORDER BY id DESC LIMIT ?", (farm_id, limit))
    else:
        cursor.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) AS total_farms FROM farms")
    total_farms = cursor.fetchone()['total_farms']
    
    cursor.execute("SELECT COUNT(*) AS total_records FROM crop_monitoring_records")
    total_records = cursor.fetchone()['total_records']
    
    cursor.execute("SELECT COUNT(*) AS total_soil_reports FROM soil_reports")
    total_soil = cursor.fetchone()['total_soil_reports']
    
    cursor.execute("SELECT * FROM farms ORDER BY id DESC LIMIT 5")
    recent_farms = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT cmr.*, f.farm_name, f.crop_selected 
        FROM crop_monitoring_records cmr 
        JOIN farms f ON cmr.farm_id = f.id 
        ORDER BY cmr.id DESC LIMIT 5
    """)
    recent_observations = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        'total_farms': total_farms,
        'total_records': total_records,
        'total_soil_reports': total_soil,
        'recent_farms': recent_farms,
        'recent_observations': recent_observations
    }
