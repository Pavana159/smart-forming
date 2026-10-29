"""
Crop Recommendation Service.
Loads the trained Random Forest Pipeline, validates inputs, performs inference,
computes probability distributions for the top candidates, and attaches agronomic explanations.
"""
import os
import joblib
import numpy as np
import pandas as pd
from config import Config

# Detailed agronomic knowledge base for the 22 benchmark crops
CROP_AGRONOMIC_KNOWLEDGE = {
    'rice': {
        'display_name': 'Rice (Paddy)',
        'category': 'Cereal / Staple',
        'seasons': ['Kharif (Monsoon)', 'Summer / Boro in irrigated zones'],
        'suitable_soils': ['Clay', 'Clay Loam', 'Silt Loam', 'Alluvial'],
        'favorable_traits': 'Thrives in warm, humid climates with abundant water supply and standing water during vegetative stages.',
        'limiting_factors': 'Highly sensitive to water scarcity; unsuited for sandy or rapid-draining soils without bunded water retention.',
        'temp_range': '20°C - 35°C', 'rainfall_pref': '> 150 mm / month'
    },
    'maize': {
        'display_name': 'Maize (Corn)',
        'category': 'Cereal / Grain',
        'seasons': ['Kharif', 'Rabi (Winter Maize in frost-free regions)', 'Spring'],
        'suitable_soils': ['Loamy', 'Sandy Loam', 'Deep Alluvial'],
        'favorable_traits': 'Efficient C4 photosynthetic metabolism; excellent response to balanced nitrogen and well-aerated seedbeds.',
        'limiting_factors': 'Extremely sensitive to waterlogging at early vegetative and tasseling stages; requires well-drained soil.',
        'temp_range': '18°C - 30°C', 'rainfall_pref': '60 - 110 mm / month'
    },
    'chickpea': {
        'display_name': 'Chickpea (Gram)',
        'category': 'Legume / Pulse',
        'seasons': ['Rabi (Cool dry winter)'],
        'suitable_soils': ['Loamy', 'Black Cotton Soil', 'Sandy Loam'],
        'favorable_traits': 'Fixes atmospheric nitrogen through symbiotic Rhizobium; highly drought-hardy with deep taproot.',
        'limiting_factors': 'Excess humidity and rain encourage Ascochyta blight and collar rot; frost at flowering aborts pods.',
        'temp_range': '15°C - 25°C', 'rainfall_pref': 'Low to Moderate (< 90 mm)'
    },
    'kidneybeans': {
        'display_name': 'Kidney Beans (Rajma)',
        'category': 'Legume / Pulse',
        'seasons': ['Rabi in plains', 'Kharif in temperate hill zones'],
        'suitable_soils': ['Loamy', 'Well-drained Fertile Soil'],
        'favorable_traits': 'High market value pulse rich in plant protein; responds well to phosphorus and potassium.',
        'limiting_factors': 'Weak nitrogen-fixing nodulation compared to other legumes; sensitive to waterlogging and salinity.',
        'temp_range': '15°C - 25°C', 'rainfall_pref': '80 - 150 mm'
    },
    'pigeonpeas': {
        'display_name': 'Pigeon Pea (Arhar / Red Gram)',
        'category': 'Legume / Pulse',
        'seasons': ['Kharif (Long duration crop)'],
        'suitable_soils': ['Loamy', 'Black Soil', 'Red Sandy Loam'],
        'favorable_traits': 'Deep taproot system opens hard subsoil layers; resilient to intermittent dry spells.',
        'limiting_factors': 'Susceptible to wilt and sterility mosaic disease under prolonged stagnant water.',
        'temp_range': '22°C - 35°C', 'rainfall_pref': '90 - 180 mm'
    },
    'mothbeans': {
        'display_name': 'Moth Bean',
        'category': 'Arid Legume / Pulse',
        'seasons': ['Kharif (Arid / Semi-Arid)'],
        'suitable_soils': ['Sandy', 'Sandy Loam', 'Light Alluvial'],
        'favorable_traits': 'One of the most drought-tolerant pulses known; thrives in arid climates with minimal irrigation.',
        'limiting_factors': 'Heavy clay soils or standing water completely destroy crop stand.',
        'temp_range': '24°C - 38°C', 'rainfall_pref': '30 - 75 mm'
    },
    'mungbean': {
        'display_name': 'Mung Bean (Green Gram)',
        'category': 'Short-duration Pulse',
        'seasons': ['Kharif', 'Summer / Zaid', 'Spring'],
        'suitable_soils': ['Loamy', 'Sandy Loam'],
        'favorable_traits': 'Rapid maturity (60-70 days); excellent green manure and catch crop in crop rotations.',
        'limiting_factors': 'Yellow Mosaic Virus (YMV) and pod shattering if rains coincide with maturity.',
        'temp_range': '25°C - 35°C', 'rainfall_pref': '40 - 70 mm'
    },
    'blackgram': {
        'display_name': 'Black Gram (Urad)',
        'category': 'Legume / Pulse',
        'seasons': ['Kharif', 'Rabi in peninsular regions'],
        'suitable_soils': ['Loamy', 'Clay Loam', 'Black Soil'],
        'favorable_traits': 'Rich in phosphoric acid; improves soil physical structure through canopy residue.',
        'limiting_factors': 'Requires warm humid weather during vegetative phase; frost or heavy late rain ruins seed quality.',
        'temp_range': '25°C - 35°C', 'rainfall_pref': '60 - 80 mm'
    },
    'lentil': {
        'display_name': 'Lentil (Masoor)',
        'category': 'Legume / Pulse',
        'seasons': ['Rabi (Cool dry winter)'],
        'suitable_soils': ['Loamy', 'Alluvial', 'Clay Loam'],
        'favorable_traits': 'Tolerates mild salinity better than chickpea; low water requirement; early winter maturity.',
        'limiting_factors': 'Poor aeration and waterlogging quickly trigger root rot and wilt.',
        'temp_range': '16°C - 26°C', 'rainfall_pref': '35 - 60 mm'
    },
    'pomegranate': {
        'display_name': 'Pomegranate',
        'category': 'Horticulture / Fruit',
        'seasons': ['Perennial (Mridu/Hasta/Ambe bahar flowering flushes)'],
        'suitable_soils': ['Sandy Loam', 'Gravelly Loam', 'Well-drained Alluvial'],
        'favorable_traits': 'Extremely hardy fruit crop; tolerant of mild drought and moderate salinity; premium market return.',
        'limiting_factors': 'Bacterial blight (Xanthomonas) and fruit cracking if soil moisture fluctuates violently during ripening.',
        'temp_range': '20°C - 35°C', 'rainfall_pref': '60 - 120 mm'
    },
    'banana': {
        'display_name': 'Banana',
        'category': 'Tropical Fruit / Plantation',
        'seasons': ['Planting Year-round in humid tropical zones'],
        'suitable_soils': ['Deep Loam', 'Clay Loam with high organic matter'],
        'favorable_traits': 'Heavy feeder yielding high biomass per hectare; rapid growth under constant warm humidity.',
        'limiting_factors': 'Demands steady water supply; extremely vulnerable to strong winds and root asphyxiation.',
        'temp_range': '22°C - 32°C', 'rainfall_pref': '> 100 mm / month'
    },
    'mango': {
        'display_name': 'Mango',
        'category': 'Tropical Fruit / Orchard',
        'seasons': ['Perennial orchard (Flowering in winter, harvest in summer)'],
        'suitable_soils': ['Deep Loam', 'Alluvial', 'Well-drained Red Loam'],
        'favorable_traits': 'Long-lived perennial with deep root system; adapted to alternating wet and dry seasons.',
        'limiting_factors': 'Rain or cloudy weather during flowering causes anthracnose and poor fruit set.',
        'temp_range': '24°C - 38°C', 'rainfall_pref': '75 - 120 mm'
    },
    'grapes': {
        'display_name': 'Grapes (Vineyard)',
        'category': 'Horticulture / Vine',
        'seasons': ['Perennial vine (Pruning in Oct/April)'],
        'suitable_soils': ['Sandy Loam', 'Gravelly Loam with subsoil drainage'],
        'favorable_traits': 'High potassium and phosphorus feeder; excellent returns under precision drip irrigation.',
        'limiting_factors': 'Downy and Powdery mildew under continuous rainfall during bunch development; requires dry ripening.',
        'temp_range': '15°C - 35°C', 'rainfall_pref': '50 - 80 mm'
    },
    'watermelon': {
        'display_name': 'Watermelon',
        'category': 'Cucurbit / Fruit',
        'seasons': ['Zaid (Summer)', 'Post-monsoon in tropical areas'],
        'suitable_soils': ['Sandy', 'Sandy Loam', 'Riverbed Alluvium'],
        'favorable_traits': 'Rapid vegetative spread; high sugar accumulation in warm sunny weather.',
        'limiting_factors': 'Frost or wet cold soil causes seedling damping-off; humid wet weather induces fruit rot.',
        'temp_range': '24°C - 32°C', 'rainfall_pref': '40 - 65 mm'
    },
    'muskmelon': {
        'display_name': 'Muskmelon (Cantaloupe)',
        'category': 'Cucurbit / Fruit',
        'seasons': ['Zaid (Summer)'],
        'suitable_soils': ['Sandy Loam', 'Riverbed Soil'],
        'favorable_traits': 'High sweetness and aroma develop under hot days and low relative humidity.',
        'limiting_factors': 'High humidity at harvest ruins netting, sugar concentration, and shelf life.',
        'temp_range': '25°C - 34°C', 'rainfall_pref': '20 - 45 mm'
    },
    'apple': {
        'display_name': 'Apple',
        'category': 'Temperate Fruit / Orchard',
        'seasons': ['Temperate Hill Perennial'],
        'suitable_soils': ['Deep Well-drained Loamy Soil'],
        'favorable_traits': 'High economic return; requires cold winter chilling hours (< 7°C) to break bud dormancy.',
        'limiting_factors': 'Will not flower or produce fruit in warm tropical or subtropical lowlands.',
        'temp_range': '12°C - 24°C', 'rainfall_pref': '100 - 130 mm'
    },
    'orange': {
        'display_name': 'Orange / Citrus',
        'category': 'Citrus Fruit / Orchard',
        'seasons': ['Subtropical Perennial'],
        'suitable_soils': ['Well-drained Loam', 'Light Alluvial'],
        'favorable_traits': 'Adaptable to mild winters and sunny summers; good drought resistance once established.',
        'limiting_factors': 'Intolerant of waterlogging (causes phytophthora root rot) and excessive salinity.',
        'temp_range': '18°C - 32°C', 'rainfall_pref': '90 - 130 mm'
    },
    'papaya': {
        'display_name': 'Papaya',
        'category': 'Tropical Fruit',
        'seasons': ['Year-round in frost-free tropical zones'],
        'suitable_soils': ['Rich Loamy Soil with excellent drainage'],
        'favorable_traits': 'Fast fruiting cycle (9-10 months from planting); continuous fruiting throughout warm seasons.',
        'limiting_factors': 'Even 24-48 hours of standing water causes collar rot and fatal tree collapse.',
        'temp_range': '22°C - 36°C', 'rainfall_pref': '120 - 200 mm'
    },
    'coconut': {
        'display_name': 'Coconut Palm',
        'category': 'Plantation / Perennial',
        'seasons': ['Coastal / Tropical Perennial'],
        'suitable_soils': ['Coastal Sand', 'Alluvial', 'Red Sandy Loam'],
        'favorable_traits': 'Highly tolerant of coastal sea breezes and light salinity; continuous monthly nut harvests.',
        'limiting_factors': 'Fails in low-humidity dry inland or frosty highland regions.',
        'temp_range': '25°C - 32°C', 'rainfall_pref': '> 130 mm'
    },
    'cotton': {
        'display_name': 'Cotton (White Gold)',
        'category': 'Fiber / Cash Crop',
        'seasons': ['Kharif'],
        'suitable_soils': ['Black Cotton Soil (Vertisol)', 'Deep Alluvial Loam'],
        'favorable_traits': 'Deep taproot; high drought recovery; responds heavily to nitrogen and sunshine.',
        'limiting_factors': 'Boll shedding if rains hit open bolls; pink bollworm susceptibility.',
        'temp_range': '22°C - 34°C', 'rainfall_pref': '60 - 100 mm'
    },
    'jute': {
        'display_name': 'Jute (Golden Fiber)',
        'category': 'Fiber / Bast Crop',
        'seasons': ['Pre-Kharif / Monsoon'],
        'suitable_soils': ['Alluvial Silt Loam', 'Clay Loam'],
        'favorable_traits': 'Thrives in river basins with high monsoon heat and abundant retting water.',
        'limiting_factors': 'Requires massive water volumes for microbial retting; cannot tolerate prolonged drought.',
        'temp_range': '24°C - 35°C', 'rainfall_pref': '150 - 250 mm'
    },
    'coffee': {
        'display_name': 'Coffee (Arabica / Robusta)',
        'category': 'Plantation / Cash Crop',
        'seasons': ['Highland Subtropical Perennial'],
        'suitable_soils': ['Rich Volcanic / Forest Loam with high organic humus'],
        'favorable_traits': 'High economic return shade crop; thrives under two-tier forest canopies.',
        'limiting_factors': 'Unsheltered direct scorching sun or frost damages foliage; requires acidic to neutral well-drained slopes.',
        'temp_range': '18°C - 28°C', 'rainfall_pref': '140 - 220 mm'
    }
}

# Model cache
_MODEL = None

def get_or_load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    
    if os.path.exists(Config.MODEL_PATH):
        try:
            _MODEL = joblib.load(Config.MODEL_PATH)
            return _MODEL
        except Exception as e:
            print(f"Error loading model from {Config.MODEL_PATH}: {e}")
    return None

def validate_crop_inputs(data):
    """
    Validates input variables and flags any missing or out-of-range values.
    Returns (is_valid, cleaned_data, missing_fields, error_message)
    """
    required_fields = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall']
    cleaned = {}
    missing = []
    
    field_ranges = {
        'nitrogen': (0, 300, 'kg/ha'),
        'phosphorus': (0, 200, 'kg/ha'),
        'potassium': (0, 300, 'kg/ha'),
        'temperature': (0.0, 50.0, '°C'),
        'humidity': (5.0, 100.0, '%'),
        'ph': (3.0, 10.0, 'pH scale'),
        'rainfall': (0.0, 500.0, 'mm')
    }
    
    for f in required_fields:
        val = data.get(f)
        if val is None or str(val).strip() == '':
            missing.append(f)
        else:
            try:
                num = float(val)
                min_v, max_v, unit = field_ranges[f]
                if not (min_v <= num <= max_v):
                    return False, None, missing, f"{f.capitalize()} ({num} {unit}) is outside realistic agricultural bounds ({min_v} to {max_v} {unit})."
                cleaned[f] = num
            except ValueError:
                return False, None, missing, f"Invalid numeric format for {f}."
                
    if missing:
        missing_names = [f.capitalize() for f in missing]
        return False, None, missing, f"Missing required measurements: {', '.join(missing_names)}. Please provide all soil and climate inputs."
        
    return True, cleaned, [], None

def recommend_crops(input_data):
    """
    Infers suitable crops using the saved scikit-learn pipeline.
    Returns up to 3 candidates with probability scores, reasoning, and limitations.
    """
    is_valid, cleaned, missing, err_msg = validate_crop_inputs(input_data)
    if not is_valid:
        return {
            'success': False,
            'error': err_msg,
            'missing_fields': missing
        }
        
    model = get_or_load_model()
    if model is None:
        return {
            'success': False,
            'error': 'Crop recommendation model is not trained or loaded yet. Run ml/train_model.py first.'
        }
        
    # Input vector: ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    feature_cols = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    df_in = pd.DataFrame([[
        cleaned['nitrogen'],
        cleaned['phosphorus'],
        cleaned['potassium'],
        cleaned['temperature'],
        cleaned['humidity'],
        cleaned['ph'],
        cleaned['rainfall']
    ]], columns=feature_cols)
    
    # Predict probabilities across all classes
    probabilities = model.predict_proba(df_in)[0]
    classes = model.classes_
    
    # Rank candidates by probability
    ranked_indices = np.argsort(probabilities)[::-1]
    
    top_candidates = []
    # Up to 3 candidates, but only include secondary ones if their probability is >= 0.05 (defensible ranking)
    top_prob = probabilities[ranked_indices[0]]
    
    for idx in ranked_indices[:3]:
        prob = probabilities[idx]
        crop_key = classes[idx].lower().strip()
        
        # Guard against fabricating arbitrary secondary candidates if probability is too low
        if len(top_candidates) >= 1 and prob < 0.04 and (top_prob - prob) > 0.85:
            break
            
        crop_info = CROP_AGRONOMIC_KNOWLEDGE.get(crop_key, {
            'display_name': crop_key.capitalize(),
            'category': 'General Field Crop',
            'seasons': ['Seasonal'],
            'suitable_soils': ['Loamy'],
            'favorable_traits': 'Matches current macronutrient and climate parameters.',
            'limiting_factors': 'Check local drainage and frost probability.',
            'temp_range': 'Standard', 'rainfall_pref': 'Standard'
        })
        
        # Build agronomic match explanation
        supporting_conditions = _explain_supporting_conditions(crop_key, cleaned)
        
        confidence_percent = round(float(prob) * 100, 1)
        
        top_candidates.append({
            'crop_key': crop_key,
            'crop_name': crop_info['display_name'],
            'category': crop_info['category'],
            'confidence_score': confidence_percent,
            'suitability_rating': 'Highly Recommended' if prob > 0.45 else 'Potentially Suitable Alternate',
            'seasons': crop_info['seasons'],
            'suitable_soils': crop_info['suitable_soils'],
            'why_suitable': crop_info['favorable_traits'],
            'supporting_conditions': supporting_conditions,
            'limitations': crop_info['limiting_factors']
        })
        
    return {
        'success': True,
        'candidates': top_candidates,
        'input_summary': cleaned,
        'disclaimer': (
            "DECISION-SUPPORT NOTICE: This crop recommendation model is trained on standard ICAR/FAO experimental "
            "reference ranges. Agricultural success depends on local microclimates, seed varieties, pest pressure, "
            "irrigation infrastructure, and market demand. Always consult your local agricultural extension officer "
            "before committing to large-scale commercial planting."
        )
    }

def _explain_supporting_conditions(crop_key, inputs):
    """
    Summarizes which specific measured parameters contributed most favorably to this crop.
    """
    reasons = []
    n, p, k = inputs['nitrogen'], inputs['phosphorus'], inputs['potassium']
    t, h, r, ph = inputs['temperature'], inputs['humidity'], inputs['rainfall'], inputs['ph']
    
    if crop_key == 'rice':
        if r > 150: reasons.append(f"Abundant rainfall ({r} mm) matches rice water requirement.")
        if h > 75: reasons.append(f"High relative humidity ({h}%) supports paddy transpiration balance.")
        if 5.5 <= ph <= 7.0: reasons.append(f"Soil pH ({ph}) is within the optimal acidic-to-neutral range.")
    elif crop_key == 'chickpea':
        if t < 22: reasons.append(f"Cool temperature ({t}°C) matches Rabi growing window.")
        if h < 35: reasons.append(f"Low humidity ({h}%) minimizes fungal Ascochyta blight risk.")
        if k > 60: reasons.append(f"High potassium ({k} kg/ha) supports pod development.")
    elif crop_key == 'cotton':
        if n > 90: reasons.append(f"Ample available nitrogen ({n} kg/ha) supports heavy vegetative branching.")
        if 20 <= t <= 32: reasons.append(f"Warm daytime temperature ({t}°C) promotes flowering.")
    elif crop_key == 'maize':
        if 18 <= t <= 28: reasons.append(f"Favorable temperature ({t}°C) for corn vegetative growth.")
        if 60 <= r <= 120: reasons.append(f"Moderate moisture ({r} mm) prevents both drought and root waterlogging.")
    elif crop_key in ['watermelon', 'muskmelon']:
        if t > 24: reasons.append(f"Warm heat ({t}°C) promotes melon vine expansion and sugar development.")
        if r < 80: reasons.append(f"Low rainfall ({r} mm) prevents fungal fruit rot.")
    elif crop_key in ['apple', 'grapes']:
        if k > 150: reasons.append(f"Very high potassium ({k} kg/ha) is vital for fruit sugar and vine vitality.")
    else:
        if 6.0 <= ph <= 7.5: reasons.append(f"Soil pH ({ph}) provides near-neutral maximum nutrient availability.")
        if 20 <= t <= 32: reasons.append(f"Temperature ({t}°C) falls into the active biological growth zone.")
        
    if not reasons:
        reasons.append("Overall balance of soil nutrients and climate fits within the model's multi-dimensional decision boundary.")
        
    return reasons
