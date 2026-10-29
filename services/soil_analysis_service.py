"""
Soil Analysis Service for Smart Farming AI.
Handles visual soil photo characterization and structured laboratory soil test reports.
Adheres strictly to agronomic honesty: visual soil photos CANNOT measure chemical NPK or pH.
"""
import os
import re
from PIL import Image, ImageStat

def analyze_soil_image(image_path):
    """
    Analyzes visual soil characteristics from a photo:
    - Dominant color (HSV / RGB)
    - Apparent texture roughness (variance of grayscale gradients)
    - Surface moisture sheen / visual darkness
    - Apparent soil type (Sandy, Loamy, Clayey, Humus-rich)
    - Explicit disclaimers separating visual traits from laboratory chemistry.
    """
    if not os.path.exists(image_path):
        return {'success': False, 'error': 'Image file not found on server.'}
    
    try:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            # Resize for fast, consistent statistical analysis
            img_thumb = img.resize((200, 200))
            stat = ImageStat.Stat(img_thumb)
            
            mean_r, mean_g, mean_b = stat.mean[:3]
            var_r, var_g, var_b = stat.var[:3]
            roughness_score = round((var_r + var_g + var_b) / 3.0, 1)
            
            # Brightness (0-255)
            brightness = round(0.299 * mean_r + 0.587 * mean_g + 0.114 * mean_b, 1)
            
            # Color classification
            # Reddish / Laterite
            is_reddish = (mean_r > mean_g * 1.2) and (mean_r > mean_b * 1.3)
            # Dark / Organic Humus
            is_dark = brightness < 85
            # Light / Sandy
            is_light_sand = brightness > 155 and (mean_r > 130 and mean_g > 120)
            
            if is_dark:
                apparent_type = 'Organic-Rich / Dark Clay Loam'
                color_description = 'Deep brown to black (high potential organic matter / high moisture retention)'
                organic_hint = 'Visual appearance suggests moderate-to-high organic debris or wet surface.'
                drainage_hint = 'Typically moderate to slow drainage; retains moisture well.'
            elif is_reddish:
                apparent_type = 'Red / Lateritic Soil'
                color_description = 'Reddish-brown (indicative of iron oxides / weathered upland soils)'
                organic_hint = 'Lateritic soils frequently have low-to-medium organic matter and phosphorus fixation.'
                drainage_hint = 'Generally porous with good internal drainage; susceptible to leaching.'
            elif is_light_sand:
                apparent_type = 'Sandy / Light Loam'
                color_description = 'Pale tan to yellowish-brown (coarse aggregate, quartz minerals)'
                organic_hint = 'Visual appearance suggests low organic matter and coarse particle size.'
                drainage_hint = 'High drainage and low water-holding capacity; quick to dry out.'
            else:
                apparent_type = 'Brown Loam / Alluvial Soil'
                color_description = 'Medium brown with balanced tonal balance'
                organic_hint = 'Visual traits resemble balanced agricultural loam.'
                drainage_hint = 'Good balance between moisture retention and aeration.'

            # Texture roughness evaluation
            if roughness_score > 1200:
                texture_desc = 'Coarse / Cloddy surface texture with visible aggregation or aggregates.'
            elif roughness_score > 600:
                texture_desc = 'Medium-grained tilth with standard seedbed crumbling.'
            else:
                texture_desc = 'Fine, smooth surface texture (fine silt/clay or pulverised dry dust).'

            # Apparent surface moisture
            if brightness < 95 and roughness_score < 800:
                moisture_appearance = 'Damp / Moist surface appearance'
            elif brightness > 140:
                moisture_appearance = 'Dry, well-aerated surface appearance'
            else:
                moisture_appearance = 'Moderate surface moisture'

            visual_observations = {
                'dominant_color_rgb': f"RGB({int(mean_r)}, {int(mean_g)}, {int(mean_b)})",
                'color_description': color_description,
                'apparent_soil_type': apparent_type,
                'surface_texture': texture_desc,
                'texture_roughness_score': roughness_score,
                'moisture_appearance': moisture_appearance,
                'organic_matter_visual_indicator': organic_hint,
                'drainage_indicator': drainage_hint
            }

            # Missing chemical measurements MUST be explicitly listed
            missing_measurements = [
                {'field': 'Nitrogen (N)', 'status': 'Missing', 'reason': 'Cannot be derived from photograph; requires laboratory chemical extraction.'},
                {'field': 'Phosphorus (P)', 'status': 'Missing', 'reason': 'Cannot be derived from photograph; requires Bray or Olsen colorimetric test.'},
                {'field': 'Potassium (K)', 'status': 'Missing', 'reason': 'Cannot be derived from photograph; requires flame photometer / ammonium acetate extraction.'},
                {'field': 'Soil pH', 'status': 'Missing', 'reason': 'Cannot be derived from photograph; requires potentiometer pH electrode test.'},
                {'field': 'Electrical Conductivity (EC)', 'status': 'Missing', 'reason': 'Cannot be derived from photograph; requires conductivity meter.'}
            ]

            summary = (
                f"Visual analysis identified {apparent_type} with a {moisture_appearance.lower()}. "
                f"Surface texture shows {texture_desc.lower()} "
                f"Note: Exact soil chemical nutrients (N, P, K, pH) cannot be determined from optical photos. "
                f"Please input laboratory soil test values for chemical fertility assessment."
            )

            return {
                'success': True,
                'report_type': 'image',
                'visual_observations': visual_observations,
                'missing_measurements': missing_measurements,
                'assessment_summary': summary,
                'scientific_disclaimer': (
                    "CRITICAL SCIENTIFIC PRINCIPLE: Optical photographs reflect surface mineral color, "
                    "roughness, and surface moisture only. They NEVER substitute for standard laboratory wet-chemistry "
                    "or sensor-measured NPK and pH. Image-based predictions of chemical quantities are scientifically unvalidated."
                )
            }

    except Exception as e:
        return {'success': False, 'error': f'Failed to process soil image: {str(e)}'}

def parse_manual_soil_report(data):
    """
    Validates and formats a laboratory soil test report entered manually or confirmed by user.
    Evaluates agronomic nutrient sufficiency levels:
    - N: Low (< 280 kg/ha or < 140 ppm), Medium, High
    - P: Low (< 23 kg/ha or < 11 ppm), Medium, High
    - K: Low (< 140 kg/ha or < 70 ppm), Medium, High
    - pH: Acidic (< 6.0), Optimal Neutral (6.0 - 7.5), Alkaline (> 7.5)
    """
    measurements = {}
    missing_measurements = []
    
    # Parse N
    n_raw = data.get('nitrogen')
    if n_raw is not None and str(n_raw).strip() != '':
        try:
            n_val = float(n_raw)
            if n_val < 0 or n_val > 1000:
                return {'success': False, 'error': 'Nitrogen value out of realistic range (0 - 1000 kg/ha).'}
            measurements['nitrogen'] = {
                'value': n_val,
                'unit': 'kg/ha',
                'rating': 'Low' if n_val < 280 else ('High' if n_val > 560 else 'Medium / Adequate'),
                'note': 'Essential for vegetative canopy growth and chlorophyll production.'
            }
        except ValueError:
            missing_measurements.append({'field': 'Nitrogen (N)', 'status': 'Invalid Format', 'reason': 'Could not parse numerical value.'})
    else:
        missing_measurements.append({'field': 'Nitrogen (N)', 'status': 'Missing', 'reason': 'Required for accurate crop fertility recommendation.'})

    # Parse P
    p_raw = data.get('phosphorus')
    if p_raw is not None and str(p_raw).strip() != '':
        try:
            p_val = float(p_raw)
            if p_val < 0 or p_val > 300:
                return {'success': False, 'error': 'Phosphorus value out of realistic range (0 - 300 kg/ha).'}
            measurements['phosphorus'] = {
                'value': p_val,
                'unit': 'kg/ha',
                'rating': 'Low' if p_val < 23 else ('High' if p_val > 56 else 'Medium / Adequate'),
                'note': 'Vital for root development, flowering, and energy transfer (ATP).'
            }
        except ValueError:
            missing_measurements.append({'field': 'Phosphorus (P)', 'status': 'Invalid Format', 'reason': 'Could not parse numerical value.'})
    else:
        missing_measurements.append({'field': 'Phosphorus (P)', 'status': 'Missing', 'reason': 'Required for root and seedling assessment.'})

    # Parse K
    k_raw = data.get('potassium')
    if k_raw is not None and str(k_raw).strip() != '':
        try:
            k_val = float(k_raw)
            if k_val < 0 or k_val > 500:
                return {'success': False, 'error': 'Potassium value out of realistic range (0 - 500 kg/ha).'}
            measurements['potassium'] = {
                'value': k_val,
                'unit': 'kg/ha',
                'rating': 'Low' if k_val < 140 else ('High' if k_val > 280 else 'Medium / Adequate'),
                'note': 'Crucial for stomatal water regulation, drought tolerance, and disease defense.'
            }
        except ValueError:
            missing_measurements.append({'field': 'Potassium (K)', 'status': 'Invalid Format', 'reason': 'Could not parse numerical value.'})
    else:
        missing_measurements.append({'field': 'Potassium (K)', 'status': 'Missing', 'reason': 'Required for plant health and water regulation.'})

    # Parse pH
    ph_raw = data.get('ph')
    if ph_raw is not None and str(ph_raw).strip() != '':
        try:
            ph_val = float(ph_raw)
            if ph_val < 3.0 or ph_val > 11.0:
                return {'success': False, 'error': 'Soil pH out of realistic range (3.0 - 11.0).'}
            
            if ph_val < 5.5:
                ph_cat = 'Strongly Acidic'
                ph_note = 'Liming may be beneficial; micronutrient toxicity possible; P availability reduced.'
            elif ph_val < 6.5:
                ph_cat = 'Moderately Acidic'
                ph_note = 'Suitable for many cereals, legumes, and acid-tolerant horticultural crops.'
            elif ph_val <= 7.5:
                ph_cat = 'Near Neutral (Ideal)'
                ph_note = 'Optimum range for maximum macronutrient availability and microbial activity.'
            elif ph_val <= 8.5:
                ph_cat = 'Moderately Alkaline'
                ph_note = 'Free carbonates likely present; iron or zinc deficiency may emerge.'
            else:
                ph_cat = 'Strongly Alkaline / Sodic'
                ph_note = 'Gypsum amendment or organic mulching may be needed.'

            measurements['ph'] = {
                'value': ph_val,
                'unit': 'pH scale',
                'rating': ph_cat,
                'note': ph_note
            }
        except ValueError:
            missing_measurements.append({'field': 'Soil pH', 'status': 'Invalid Format', 'reason': 'Could not parse numerical value.'})
    else:
        missing_measurements.append({'field': 'Soil pH', 'status': 'Missing', 'reason': 'Critical for determining nutrient availability.'})

    # Optional Organic Carbon
    oc_raw = data.get('organic_carbon')
    if oc_raw is not None and str(oc_raw).strip() != '':
        try:
            oc_val = float(oc_raw)
            measurements['organic_carbon'] = {
                'value': oc_val,
                'unit': '% OC',
                'rating': 'Low (<0.5%)' if oc_val < 0.5 else ('High (>0.75%)' if oc_val > 0.75 else 'Medium'),
                'note': 'Indicator of soil biological activity and cation exchange capacity.'
            }
        except ValueError:
            pass

    # Optional Electrical Conductivity
    ec_raw = data.get('electrical_conductivity')
    if ec_raw is not None and str(ec_raw).strip() != '':
        try:
            ec_val = float(ec_raw)
            measurements['electrical_conductivity'] = {
                'value': ec_val,
                'unit': 'dS/m',
                'rating': 'Normal (<1.0)' if ec_val < 1.0 else ('Slightly Saline (1.0-2.0)' if ec_val <= 2.0 else 'Saline (>2.0)'),
                'note': 'Measure of soluble salt concentration and salinity hazard.'
            }
        except ValueError:
            pass

    soil_texture = data.get('soil_texture', 'Loamy')
    
    # Generate assessment summary
    summary_parts = []
    if 'ph' in measurements:
        summary_parts.append(f"Soil reaction is {measurements['ph']['rating']} (pH {measurements['ph']['value']}).")
    if 'nitrogen' in measurements:
        summary_parts.append(f"Nitrogen is rated as {measurements['nitrogen']['rating']}.")
    if 'phosphorus' in measurements:
        summary_parts.append(f"Phosphorus is rated as {measurements['phosphorus']['rating']}.")
    if 'potassium' in measurements:
        summary_parts.append(f"Potassium is rated as {measurements['potassium']['rating']}.")

    if missing_measurements:
        summary_parts.append(f"{len(missing_measurements)} parameter(s) missing from report.")
    
    summary = " ".join(summary_parts) if summary_parts else "Laboratory soil report received."

    return {
        'success': True,
        'report_type': 'test_report',
        'measurements': measurements,
        'soil_texture': soil_texture,
        'missing_measurements': missing_measurements,
        'assessment_summary': summary,
        'has_all_critical': len(missing_measurements) == 0
    }

def extract_text_from_report_file(file_path):
    """
    Extracts text and attempts regex heuristics to extract N, P, K, and pH from
    uploaded text or PDF reports for user review and confirmation.
    """
    if not os.path.exists(file_path):
        return {'success': False, 'error': 'File not found'}
    
    text_content = ""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
        except Exception as e:
            return {'success': False, 'error': f'Failed reading text file: {str(e)}'}
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text_content += page.extract_text() or ""
        except ImportError:
            # Fallback simple string read if pypdf is not installed
            try:
                with open(file_path, 'rb') as f:
                    raw = f.read().decode('latin-1', errors='ignore')
                    # Extract printable ASCII words
                    text_content = " ".join(re.findall(r'[a-zA-Z0-9\.\:\=\-\s]{3,}', raw))
            except Exception:
                text_content = ""
    else:
        return {'success': False, 'error': 'Unsupported file format for direct text parsing. Please input values manually.'}

    extracted = {}
    
    # Regex heuristics for N, P, K, pH
    n_match = re.search(r'(?:nitrogen|available\s*n|n)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if n_match:
        extracted['nitrogen'] = float(n_match.group(1))

    p_match = re.search(r'(?:phosphorus|available\s*p|p2o5|p)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if p_match:
        extracted['phosphorus'] = float(p_match.group(1))

    k_match = re.search(r'(?:potassium|potash|k2o|k)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if k_match:
        extracted['potassium'] = float(k_match.group(1))

    ph_match = re.search(r'(?:ph|reaction)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if ph_match:
        extracted['ph'] = float(ph_match.group(1))

    oc_match = re.search(r'(?:organic\s*carbon|oc)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if oc_match:
        extracted['organic_carbon'] = float(oc_match.group(1))

    ec_match = re.search(r'(?:electrical\s*conductivity|ec)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)', text_content, re.IGNORECASE)
    if ec_match:
        extracted['electrical_conductivity'] = float(ec_match.group(1))

    return {
        'success': True,
        'extracted_fields': extracted,
        'raw_text_preview': text_content[:500] if text_content else 'No machine-readable text detected.'
    }
