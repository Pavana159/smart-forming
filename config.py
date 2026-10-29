"""
Configuration module for Smart Farming AI application.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-farming-ai-secret-key-college-project-2026')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'smart_farming.db'))
    
    # Upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'static', 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    ALLOWED_REPORT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'txt'}
    
    # Open-Meteo Weather APIs (No API key required)
    OPEN_METEO_WEATHER_URL = 'https://api.open-meteo.com/v1/forecast'
    OPEN_METEO_GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
    
    # Optional Gemini Vision API key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    
    # Model Paths
    MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'crop_model.joblib')
    MODEL_METRICS_PATH = os.path.join(BASE_DIR, 'ml', 'model_metrics.json')
