"""
Crop Image Analysis Service.
Performs quantitative computer vision on crop foliage photographs:
- Excess Green Index (ExG = 2G - R - B)
- Canopy coverage percentage
- Chlorosis (leaf yellowing) detection
- Necrosis / brown spot identification
- Temporal progression comparison against historical observations
- Strict agronomic limitations and scientific disclaimers
"""
import os
from PIL import Image, ImageStat
from config import Config

ALLOWED_STAGES = [
    'Immediately after planting',
    'Seedling growth',
    'Vegetative growth',
    'Flowering',
    'Fruiting or grain formation',
    'Near harvest'
]

def analyze_crop_image(image_path, crop_name='Crop', growth_stage='Vegetative growth', previous_record=None):
    """
    Analyzes visible crop foliage characteristics from a photograph.
    Computes vegetation indices, symptomatic color shifts, and comparison with history.
    """
    if not os.path.exists(image_path):
        return {'success': False, 'error': 'Image file not found on server.'}
        
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            # Sample to 300x300 for reliable pixel statistic computation
            w, h = 300, 300
            thumb = img.resize((w, h))
            if hasattr(thumb, 'get_flattened_data'):
                pixels = list(thumb.get_flattened_data())
            else:
                pixels = list(thumb.getdata())
            total_pixels = len(pixels)
            
            green_pixels = 0
            yellow_pixels = 0
            brown_spot_pixels = 0
            exg_sum = 0.0
            
            for r, g, b in pixels:
                # Excess Green Index: ExG = 2*G - R - B (Normalized -255 to +510)
                exg = (2 * g) - r - b
                exg_sum += exg
                
                # Vegetation pixel identification: green dominant over red and blue
                if g > r and g > b and g > 45:
                    green_pixels += 1
                    
                # Chlorosis / Yellowing: High R and G with significantly lower B
                # E.g. R > 120, G > 120, B < 90, and |R - G| < 40
                if r > 115 and g > 115 and b < 95 and abs(r - g) < 45:
                    yellow_pixels += 1
                    
                # Necrosis / Brown Spots: Dark brownish/tan discoloration
                # E.g. R > 80, G < 75, B < 65 and G > B
                if 70 < r < 180 and 40 < g < 130 and b < 80 and (r > g + 15):
                    brown_spot_pixels += 1
                    
            mean_exg = round(exg_sum / total_pixels, 2)
            canopy_pct = round((green_pixels / total_pixels) * 100, 1)
            chlorosis_pct = round((yellow_pixels / total_pixels) * 100, 1)
            necrosis_pct = round((brown_spot_pixels / total_pixels) * 100, 1)
            
            # Exposure / quality check
            stat = ImageStat.Stat(thumb)
            brightness = sum(stat.mean[:3]) / 3.0
            
            is_overexposed = brightness > 220
            is_underexposed = brightness < 40
            
            symptoms = []
            if chlorosis_pct > 22.0:
                symptoms.append('Noticeable leaf yellowing (chlorosis) on foliage')
            elif chlorosis_pct > 10.0:
                symptoms.append('Mild foliage pale tint / slight chlorosis')
                
            if necrosis_pct > 7.0:
                symptoms.append('Brown leaf spots / marginal necrotic lesions')
            elif necrosis_pct > 2.5:
                symptoms.append('Scattered brown speckles or dry tips')
                
            if canopy_pct < 8.0 and growth_stage in ['Vegetative growth', 'Flowering', 'Fruiting or grain formation']:
                symptoms.append('Sparse vegetative canopy for current recorded growth stage')
                
            # Classify overall health status
            if is_overexposed or is_underexposed:
                health_status = 'Uncertain'
                confidence = 0.50
                symptoms.append('Image lighting conditions make optical foliage assessment uncertain.')
            elif chlorosis_pct > 25.0 or necrosis_pct > 8.0:
                health_status = 'Moderate Stress'
                confidence = 0.82
            elif chlorosis_pct > 35.0 or necrosis_pct > 14.0:
                health_status = 'Severe Stress'
                confidence = 0.86
            elif chlorosis_pct > 9.0 or necrosis_pct > 3.0:
                health_status = 'Mild Stress'
                confidence = 0.85
            else:
                health_status = 'Healthy'
                confidence = 0.90
                
            # Comparison with previous record
            comparison_notes = _generate_comparison_notes(
                current_metrics={
                    'canopy': canopy_pct, 'exg': mean_exg,
                    'chlorosis': chlorosis_pct, 'necrosis': necrosis_pct,
                    'stage': growth_stage
                },
                prev_record=previous_record
            )
            
            disclaimer = (
                "MONITORING LIMITATIONS: Visual photo analysis identifies chromatic foliage traits "
                "(chlorosis, necrotic spotting, canopy density) under standard ambient lighting. It cannot identify "
                "specific sub-microscopic pathogens (viruses, bacteria, vascular wilt fungi) or subterranean nematode "
                "damage. If crop stress persists, physical field inspection and local agronomist consultation are advised."
            )
            
            return {
                'success': True,
                'growth_stage': growth_stage,
                'health_status': health_status,
                'confidence_score': confidence,
                'greenness_index': mean_exg,
                'canopy_coverage': canopy_pct,
                'chlorosis_yellowing': chlorosis_pct,
                'necrosis_spots': necrosis_pct,
                'visible_symptoms': symptoms,
                'comparison_notes': comparison_notes,
                'limitations_disclaimer': disclaimer
            }
            
    except Exception as e:
        return {'success': False, 'error': f'Failed to analyze crop photo: {str(e)}'}

def _generate_comparison_notes(current_metrics, prev_record):
    """
    Compares current observation with historical record for this farm.
    """
    if not prev_record:
        return f"Initial baseline photo recorded for stage '{current_metrics['stage']}'. Canopy coverage is {current_metrics['canopy']}%. Future uploads will be compared against this baseline."
        
    prev_canopy = prev_record.get('canopy_coverage', 0.0)
    prev_stage = prev_record.get('growth_stage', 'Earlier Stage')
    prev_date = prev_record.get('observation_date', 'earlier')
    prev_chlorosis = prev_record.get('chlorosis_yellowing', 0.0)
    prev_necrosis = prev_record.get('necrosis_spots', 0.0)
    
    canopy_diff = round(current_metrics['canopy'] - prev_canopy, 1)
    chlorosis_diff = round(current_metrics['chlorosis'] - prev_chlorosis, 1)
    necrosis_diff = round(current_metrics['necrosis'] - prev_necrosis, 1)
    
    notes = []
    # Canopy trend
    if canopy_diff > 3.0:
        notes.append(f"Canopy coverage increased by +{canopy_diff}% compared to {prev_date} ({prev_stage}), indicating active vegetative biomass expansion.")
    elif canopy_diff < -5.0:
        notes.append(f"Canopy coverage decreased by {abs(canopy_diff)}% compared to {prev_date}. Verify whether defoliation, pruning, or leaf curl has occurred.")
    else:
        notes.append(f"Canopy coverage remained steady ({current_metrics['canopy']}%) relative to {prev_date}.")
        
    # Yellowing / Chlorosis trend
    if chlorosis_diff > 5.0:
        notes.append(f"Leaf yellowing increased by +{chlorosis_diff}%. Monitor for nitrogen deficiency, waterlogging, or early leaf senescence.")
    elif chlorosis_diff < -4.0:
        notes.append(f"Leaf greenness recovered with chlorosis decreasing by {abs(chlorosis_diff)}%, reflecting improved plant vigor.")
        
    # Spot / Necrosis trend
    if necrosis_diff > 3.0:
        notes.append(f"New brown spotting detected (+{necrosis_diff}% increase). Inspect foliage undersides for fungal spots or insect feeding punctures.")
    elif necrosis_diff < 0.0:
        notes.append("No expansion in necrotic spots observed.")
        
    return " ".join(notes)
