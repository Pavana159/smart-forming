"""
Weather Service using Open-Meteo API.
Fetches live weather and 7-day forecast without requiring an API key.
Supports geolocation, city name search, recent rainfall, and manual fallback.
"""
import requests
import datetime
from config import Config

# Simple in-memory cache to respect API etiquette (key: lat_lon_rounded -> (timestamp, data))
_WEATHER_CACHE = {}
CACHE_DURATION_SECONDS = 300  # 5 minutes

def search_location(query):
    """
    Search coordinates by city/region name using Open-Meteo Geocoding.
    Returns list of dicts with name, country, admin1, latitude, longitude.
    """
    if not query or len(query.strip()) < 2:
        return {'success': False, 'error': 'Please enter a valid city or district name.'}
    
    try:
        response = requests.get(
            Config.OPEN_METEO_GEOCODING_URL,
            params={'name': query.strip(), 'count': 5, 'language': 'en', 'format': 'json'},
            timeout=8
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if not results:
                return {'success': False, 'error': f'No locations found matching "{query}".'}
            
            clean_results = []
            for r in results:
                name_parts = [r.get('name')]
                if r.get('admin1'):
                    name_parts.append(r.get('admin1'))
                if r.get('country'):
                    name_parts.append(r.get('country'))
                
                clean_results.append({
                    'display_name': ', '.join(name_parts),
                    'city': r.get('name'),
                    'region': r.get('admin1', ''),
                    'country': r.get('country', ''),
                    'latitude': r.get('latitude'),
                    'longitude': r.get('longitude')
                })
            return {'success': True, 'locations': clean_results}
        else:
            return {'success': False, 'error': f'Geocoding server responded with status {response.status_code}.'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Network error connecting to geocoding service: {str(e)}'}

def get_live_weather(lat, lon, location_name='Selected Field'):
    """
    Fetch current conditions and 7-day forecast from Open-Meteo.
    Includes temperature, relative humidity, precipitation, and past rain.
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return {'success': False, 'error': 'Invalid latitude or longitude coordinates.'}
    
    cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
    now_ts = datetime.datetime.now().timestamp()
    if cache_key in _WEATHER_CACHE:
        cache_time, cached_data = _WEATHER_CACHE[cache_key]
        if now_ts - cache_time < CACHE_DURATION_SECONDS:
            cached_data['from_cache'] = True
            return cached_data

    params = {
        'latitude': lat,
        'longitude': lon,
        'current': [
            'temperature_2m', 'relative_humidity_2m', 'apparent_temperature',
            'precipitation', 'rain', 'weather_code', 'wind_speed_10m'
        ],
        'hourly': [
            'temperature_2m', 'relative_humidity_2m', 'precipitation_probability', 'precipitation'
        ],
        'daily': [
            'weather_code', 'temperature_2m_max', 'temperature_2m_min',
            'precipitation_sum', 'precipitation_probability_max'
        ],
        'past_days': 2,
        'forecast_days': 7,
        'timezone': 'auto'
    }

    try:
        response = requests.get(Config.OPEN_METEO_WEATHER_URL, params=params, timeout=10)
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'Open-Meteo API returned status code {response.status_code}. Live weather unavailable.'
            }
        
        data = response.json()
        current = data.get('current', {})
        daily = data.get('daily', {})
        
        # Calculate recent rainfall from past 2 days
        daily_rain = daily.get('precipitation_sum', [])
        past_rain_sum = 0.0
        if len(daily_rain) >= 2:
            past_rain_sum = round(sum([r for r in daily_rain[:2] if r is not None]), 1)
            
        forecast_rain_sum = 0.0
        if len(daily_rain) > 2:
            forecast_rain_sum = round(sum([r for r in daily_rain[2:5] if r is not None]), 1)

        # Weather Code Interpretation (WMO codes)
        wmo_code = current.get('weather_code', 0)
        condition_desc, icon_class = _interpret_wmo_code(wmo_code)

        # 7-day Daily forecast breakdown
        daily_forecast = []
        dates = daily.get('time', [])
        max_temps = daily.get('temperature_2m_max', [])
        min_temps = daily.get('temperature_2m_min', [])
        rain_sums = daily.get('precipitation_sum', [])
        wmo_codes = daily.get('weather_code', [])
        rain_probs = daily.get('precipitation_probability_max', [])

        for i in range(len(dates)):
            # Skip past days in the forward-looking forecast UI
            day_wmo = wmo_codes[i] if i < len(wmo_codes) else 0
            day_desc, day_icon = _interpret_wmo_code(day_wmo)
            daily_forecast.append({
                'date': dates[i],
                'day_name': datetime.datetime.strptime(dates[i], '%Y-%m-%d').strftime('%a'),
                'temp_max': max_temps[i] if i < len(max_temps) else None,
                'temp_min': min_temps[i] if i < len(min_temps) else None,
                'rain_sum': rain_sums[i] if i < len(rain_sums) else 0.0,
                'rain_probability': rain_probs[i] if i < len(rain_probs) else 0,
                'condition': day_desc,
                'icon': day_icon,
                'is_today': (i == 2)  # because past_days=2
            })

        # Chart-ready forecast series (next 5 days)
        future_forecast = [d for d in daily_forecast if not dates.index(d['date']) < 2]

        result = {
            'success': True,
            'source': 'Open-Meteo Weather API (WMO compliant)',
            'timestamp': current.get('time', datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')),
            'location_name': location_name,
            'latitude': lat,
            'longitude': lon,
            'temperature': current.get('temperature_2m'),
            'feels_like': current.get('apparent_temperature'),
            'humidity': current.get('relative_humidity_2m'),
            'precipitation_current': current.get('precipitation', 0.0),
            'wind_speed': current.get('wind_speed_10m', 0.0),
            'weather_code': wmo_code,
            'condition': condition_desc,
            'icon': icon_class,
            'recent_rain_48h': past_rain_sum,
            'forecast_rain_next_3days': forecast_rain_sum,
            'daily_forecast': future_forecast,
            'from_cache': False
        }

        _WEATHER_CACHE[cache_key] = (now_ts, result)
        return result

    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Open-Meteo Weather request timed out. You may use manual entry.'}
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Failed to retrieve weather data: {str(e)}. You may use manual entry.'}

def format_manual_weather(temperature, humidity, rainfall, location_name='Manual Station'):
    """
    Creates a standardized weather payload when the farmer inputs data manually.
    """
    try:
        temp = float(temperature)
        hum = float(humidity)
        rain = float(rainfall)
    except (ValueError, TypeError):
        return {'success': False, 'error': 'Invalid numeric values for temperature, humidity, or rainfall.'}

    if not (-20 <= temp <= 60):
        return {'success': False, 'error': 'Temperature must be between -20°C and 60°C.'}
    if not (0 <= hum <= 100):
        return {'success': False, 'error': 'Relative humidity must be between 0% and 100%.'}
    if not (0 <= rain <= 1000):
        return {'success': False, 'error': 'Rainfall must be between 0 mm and 1000 mm.'}

    return {
        'success': True,
        'source': 'Manual Farm Entry (Farmer-provided)',
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'location_name': location_name,
        'temperature': temp,
        'feels_like': temp,
        'humidity': hum,
        'precipitation_current': 0.0,
        'wind_speed': 0.0,
        'condition': 'Manual Reading',
        'icon': 'bi-thermometer-half',
        'recent_rain_48h': rain,
        'forecast_rain_next_3days': 0.0,
        'daily_forecast': [],
        'is_manual': True
    }

def _interpret_wmo_code(code):
    """
    Translates standard WMO weather codes into human-readable description and Bootstrap icon.
    """
    code_map = {
        0: ('Clear sky', 'bi-sun-fill text-warning'),
        1: ('Mainly clear', 'bi-cloud-sun text-warning'),
        2: ('Partly cloudy', 'bi-cloud-sun text-secondary'),
        3: ('Overcast', 'bi-clouds-fill text-secondary'),
        45: ('Fog', 'bi-cloud-haze2 text-muted'),
        48: ('Depositing rime fog', 'bi-cloud-fog2 text-muted'),
        51: ('Light drizzle', 'bi-cloud-drizzle text-info'),
        53: ('Moderate drizzle', 'bi-cloud-drizzle-fill text-info'),
        55: ('Dense drizzle', 'bi-cloud-rain text-primary'),
        61: ('Slight rain', 'bi-cloud-rain text-info'),
        63: ('Moderate rain', 'bi-cloud-rain-heavy text-primary'),
        65: ('Heavy rain', 'bi-cloud-rain-heavy-fill text-primary'),
        71: ('Slight snowfall', 'bi-snow text-info'),
        73: ('Moderate snowfall', 'bi-snow2 text-info'),
        75: ('Heavy snowfall', 'bi-snow3 text-primary'),
        80: ('Slight rain showers', 'bi-cloud-rain text-info'),
        81: ('Moderate rain showers', 'bi-cloud-rain-heavy text-primary'),
        82: ('Violent rain showers', 'bi-cloud-lightning-rain-fill text-danger'),
        95: ('Thunderstorm', 'bi-cloud-lightning text-danger'),
        96: ('Thunderstorm with slight hail', 'bi-cloud-lightning-fill text-danger'),
        99: ('Thunderstorm with heavy hail', 'bi-cloud-lightning-rain-fill text-danger')
    }
    return code_map.get(code, ('Variable weather', 'bi-cloud text-secondary'))
