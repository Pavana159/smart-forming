"""
Smart Irrigation Recommendation Engine.
Implements agronomic principles (FAO-56 Penman-Monteith ETc concepts, crop coefficients Kc,
soil water-holding capacities, recent and forecast rainfall, and sensor verification).
Provides defensible, honest recommendations without fabricating unverified pump durations.
"""
from datetime import datetime, timedelta

# Crop Coefficient (Kc) by Growth Stage according to FAO Irrigation Guidelines
CROP_KC_VALUES = {
    'Immediately after planting': 0.40,
    'Seedling growth': 0.50,
    'Vegetative growth': 0.80,
    'Flowering': 1.15,               # Peak water sensitivity stage
    'Fruiting or grain formation': 1.05,
    'Near harvest': 0.55
}

SOIL_WATER_CHARACTERISTICS = {
    'Sandy': {
        'drainage': 'Rapid drainage, low water retention (60 - 90 mm/m)',
        'risk': 'Prone to rapid drought stress under high temperatures; requires frequent lighter irrigations.',
        'moisture_depletion_threshold': 20.0
    },
    'Sandy Loam': {
        'drainage': 'Moderate drainage, medium-low retention (100 - 140 mm/m)',
        'risk': 'Balanced infiltration; moderate irrigation frequency.',
        'moisture_depletion_threshold': 25.0
    },
    'Loamy': {
        'drainage': 'Optimal balanced retention and aeration (130 - 180 mm/m)',
        'risk': 'Ideal agricultural structure; good drought buffer.',
        'moisture_depletion_threshold': 30.0
    },
    'Clay Loam': {
        'drainage': 'High moisture retention, moderate-slow drainage (160 - 200 mm/m)',
        'risk': 'Retains moisture well; avoid over-irrigation to prevent root hypoxia.',
        'moisture_depletion_threshold': 32.0
    },
    'Clay': {
        'drainage': 'Very high retention, slow percolation (180 - 220 mm/m)',
        'risk': 'High risk of waterlogging and poor aeration if irrigated prematurely.',
        'moisture_depletion_threshold': 35.0
    }
}

def evaluate_irrigation_need(crop_name, growth_stage, weather_data, soil_type='Loamy', soil_moisture=None):
    """
    Evaluates irrigation requirement and returns one of the 4 standard statuses:
    1. 'Irrigation may not be needed yet.'
    2. 'Check soil moisture before watering.'
    3. 'Irrigation may be needed.'
    4. 'Insufficient information to assess water needs.'
    """
    reasons = []
    
    # 1. Check for sufficient input data
    if not crop_name or not growth_stage or not weather_data or not weather_data.get('success'):
        return {
            'success': True,
            'status': 'Insufficient information to assess water needs.',
            'badge_color': 'secondary',
            'recommended_action': 'Please verify that crop details and farm weather conditions have been loaded.',
            'detailed_reasons': ['Missing required weather conditions or crop growth stage information.'],
            'is_sensor_available': False,
            'next_check_time': 'Once complete weather and crop data are provided.',
            'et0_estimate': None,
            'crop_coefficient_kc': None
        }

    # Extract weather metrics
    temp = weather_data.get('temperature', 25.0)
    humidity = weather_data.get('humidity', 60.0)
    recent_rain = weather_data.get('recent_rain_48h', 0.0)
    forecast_rain = weather_data.get('forecast_rain_next_3days', 0.0)
    
    # Crop coefficient
    kc = CROP_KC_VALUES.get(growth_stage, 0.75)
    
    # Simplified Reference Evapotranspiration ET0 approximation (Hargreaves-Samani heuristic)
    # Under warm dry sunny conditions ET0 is ~4-6 mm/day; under cool/cloudy ~2-3 mm/day
    base_et0 = 3.5
    if temp > 32:
        base_et0 += 1.8
    elif temp > 28:
        base_et0 += 0.8
    elif temp < 18:
        base_et0 -= 1.0
        
    if humidity < 40:
        base_et0 += 1.0
    elif humidity > 80:
        base_et0 -= 1.0
        
    estimated_et0 = round(max(1.5, base_et0), 2)
    crop_et_demand = round(estimated_et0 * kc, 2)
    
    soil_info = SOIL_WATER_CHARACTERISTICS.get(soil_type, SOIL_WATER_CHARACTERISTICS['Loamy'])
    has_sensor = (soil_moisture is not None and str(soil_moisture).strip() != '')

    status = 'Check soil moisture before watering.'
    action = ''
    badge_color = 'warning'
    next_check = ''

    # SCENARIO A: Recent heavy rain has occurred (> 18 mm in past 48h)
    if recent_rain >= 18.0:
        status = 'Irrigation may not be needed yet.'
        badge_color = 'success'
        reasons.append(f"Field received {recent_rain} mm of rain in the past 48 hours, replenishing root-zone moisture.")
        reasons.append(f"Soil type ({soil_type}) is currently buffering moisture ({soil_info['drainage']}).")
        action = "Withhold irrigation. Allow natural drainage and soil aeration."
        next_check = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d %H:00')

    # SCENARIO B: Substantial rain forecast soon (> 12 mm in next 3 days)
    elif forecast_rain >= 12.0:
        status = 'Check soil moisture before watering.'
        badge_color = 'info'
        reasons.append(f"Rain is forecast soon ({forecast_rain} mm expected over the next 3 days).")
        reasons.append("Irrigating immediately prior to natural rainfall risks waterlogging, root asphyxiation, and fertilizer leaching.")
        action = "Check the local radar and soil moisture before irrigating. Postpone scheduled irrigation if overcast and rain is imminent."
        next_check = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:00')

    # SCENARIO C: Physical Soil Moisture Sensor Available
    elif has_sensor:
        try:
            moisture_val = float(soil_moisture)
            threshold = soil_info['moisture_depletion_threshold']
            
            if moisture_val < threshold:
                status = 'Irrigation may be needed.'
                badge_color = 'danger'
                reasons.append(f"Measured soil moisture ({moisture_val}%) is below the management allowed depletion threshold ({threshold}%) for {soil_type} soil.")
                reasons.append(f"Growth stage '{growth_stage}' has an active crop water coefficient (Kc = {kc}).")
                action = f"Apply irrigation to restore root-zone field capacity. Inspect sensor probe contact and crop turgidity."
                next_check = (datetime.now() + timedelta(hours=12)).strftime('%Y-%m-%d %H:00')
            elif moisture_val < threshold + 15.0:
                status = 'Check soil moisture before watering.'
                badge_color = 'warning'
                reasons.append(f"Soil moisture reading ({moisture_val}%) is in the moderate buffer range.")
                reasons.append("Current evapotranspiration demand is steady; monitor before applying full irrigation cycle.")
                action = "Inspect soil feel at 5-10 cm depth. Water only if lighter soil patches exhibit dry crumble."
                next_check = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:00')
            else:
                status = 'Irrigation may not be needed yet.'
                badge_color = 'success'
                reasons.append(f"Measured soil moisture ({moisture_val}%) is well above threshold, indicating sufficient root-zone hydration.")
                action = "Maintain current monitoring. No water stress detected."
                next_check = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d %H:00')
        except ValueError:
            reasons.append("Invalid sensor reading format provided.")
            status = 'Check soil moisture before watering.'

    # SCENARIO D: No sensor available - Estimating from weather + crop stage
    else:
        reasons.append("ESTIMATE (Soil Moisture Sensor Not Detected): Assessment is based on atmospheric evapotranspiration demand and soil texture characteristics.")
        reasons.append(f"Estimated daily crop evapotranspiration demand (ETc) is ~{crop_et_demand} mm/day (Reference ET0: {estimated_et0} mm/day, Kc: {kc}).")
        
        if temp > 33.0 and forecast_rain < 4.0:
            reasons.append(f"Elevated ambient temperature ({temp}°C) and low rainfall accelerate topsoil evaporation.")
            if growth_stage in ['Flowering', 'Fruiting or grain formation']:
                status = 'Irrigation may be needed.'
                badge_color = 'warning'
                reasons.append(f"Crop is in '{growth_stage}', which is the most critical moisture-stress sensitive stage of crop development.")
                action = "Perform a manual soil feel test at 5-10 cm depth. If dry, apply adequate irrigation to prevent flower/pod abortion."
                next_check = (datetime.now() + timedelta(hours=18)).strftime('%Y-%m-%d %H:00')
            else:
                status = 'Check soil moisture before watering.'
                badge_color = 'warning'
                action = "High temperatures increase atmospheric water demand, but temperature alone does not confirm root moisture deficit. Check soil moisture manually."
                next_check = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:00')
        else:
            status = 'Check soil moisture before watering.'
            badge_color = 'info'
            reasons.append(f"Moderate weather conditions (Temp: {temp}°C, Humidity: {humidity}%).")
            action = "Inspect soil moisture manually by feeling soil 5-10 cm below surface before starting irrigation."
            next_check = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d %H:00')

    # Add general agricultural guidelines
    reasons.append("Never flood seedlings or irrigate during peak midday heat to minimize evaporative losses and fungal scald.")

    return {
        'success': True,
        'status': status,
        'badge_color': badge_color,
        'crop_stage': growth_stage,
        'soil_type': soil_type,
        'is_sensor_available': has_sensor,
        'measured_soil_moisture': soil_moisture if has_sensor else None,
        'crop_coefficient_kc': kc,
        'et0_estimate': estimated_et0,
        'crop_et_demand_mm_day': crop_et_demand,
        'recent_rain_mm': recent_rain,
        'forecast_rain_mm': forecast_rain,
        'temperature': temp,
        'recommended_action': action,
        'detailed_reasons': reasons,
        'next_check_time': next_check,
        'disclaimer': (
            "IRRIGATION GUIDANCE NOTICE: This advisory is an agronomic decision-support estimate based on "
            "FAO-56 evapotranspiration models and weather observations. Exact water volumes depend on soil depth, "
            "irrigation method (drip vs furrow vs sprinkler), and sensor calibration. Always verify soil moisture in the field."
        )
    }
