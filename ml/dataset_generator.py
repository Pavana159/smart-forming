"""
Dataset generator for the Crop Recommendation Dataset.
Generates the benchmark 2,200 row Kaggle/ICAR-aligned dataset covering 22 major crops
across 7 vital soil & weather parameters:
N (Nitrogen), P (Phosphorus), K (Potassium), Temperature (°C), Humidity (%), pH, Rainfall (mm).
"""
import os
import csv
import random

# Seed for absolute reproducibility
random.seed(42)

CROPS_DISTRIBUTION = {
    'rice': {'N': (80, 10), 'P': (47, 8), 'K': (40, 5), 'temp': (23.6, 2.5), 'humidity': (82.2, 3.5), 'ph': (6.4, 0.4), 'rainfall': (236, 35)},
    'maize': {'N': (77, 12), 'P': (48, 8), 'K': (20, 3), 'temp': (22.3, 3.0), 'humidity': (65.0, 5.5), 'ph': (6.2, 0.5), 'rainfall': (84, 15)},
    'chickpea': {'N': (40, 10), 'P': (67, 8), 'K': (79, 4), 'temp': (18.8, 1.5), 'humidity': (16.8, 2.2), 'ph': (7.3, 0.5), 'rainfall': (80, 10)},
    'kidneybeans': {'N': (20, 8), 'P': (67, 8), 'K': (20, 3), 'temp': (20.1, 2.8), 'humidity': (21.6, 2.5), 'ph': (5.7, 0.3), 'rainfall': (105, 25)},
    'pigeonpeas': {'N': (20, 8), 'P': (67, 8), 'K': (20, 3), 'temp': (27.7, 3.5), 'humidity': (48.0, 8.0), 'ph': (5.7, 0.7), 'rainfall': (149, 30)},
    'mothbeans': {'N': (21, 8), 'P': (48, 8), 'K': (20, 3), 'temp': (28.1, 2.5), 'humidity': (53.1, 6.5), 'ph': (6.8, 1.2), 'rainfall': (51, 12)},
    'mungbean': {'N': (20, 8), 'P': (47, 8), 'K': (20, 3), 'temp': (28.5, 1.8), 'humidity': (85.5, 3.2), 'ph': (6.7, 0.3), 'rainfall': (48, 8)},
    'blackgram': {'N': (40, 8), 'P': (67, 8), 'K': (19, 3), 'temp': (29.9, 2.8), 'humidity': (65.1, 4.0), 'ph': (7.1, 0.3), 'rainfall': (67, 6)},
    'lentil': {'N': (18, 7), 'P': (68, 7), 'K': (19, 3), 'temp': (24.5, 3.5), 'humidity': (64.8, 4.2), 'ph': (6.9, 0.4), 'rainfall': (45, 6)},
    'pomegranate': {'N': (18, 8), 'P': (18, 5), 'K': (40, 3), 'temp': (21.8, 2.2), 'humidity': (90.1, 3.0), 'ph': (6.4, 0.4), 'rainfall': (107, 6)},
    'banana': {'N': (100, 12), 'P': (82, 8), 'K': (50, 4), 'temp': (27.3, 1.5), 'humidity': (80.3, 3.0), 'ph': (5.9, 0.3), 'rainfall': (104, 10)},
    'mango': {'N': (20, 8), 'P': (27, 6), 'K': (30, 3), 'temp': (31.2, 2.8), 'humidity': (50.1, 3.5), 'ph': (5.7, 0.7), 'rainfall': (94, 6)},
    'grapes': {'N': (23, 8), 'P': (132, 8), 'K': (200, 4), 'temp': (23.8, 8.0), 'humidity': (81.8, 2.0), 'ph': (6.0, 0.3), 'rainfall': (69, 4)},
    'watermelon': {'N': (99, 12), 'P': (17, 6), 'K': (50, 4), 'temp': (25.5, 1.2), 'humidity': (85.1, 3.0), 'ph': (6.4, 0.3), 'rainfall': (50, 6)},
    'muskmelon': {'N': (100, 11), 'P': (17, 6), 'K': (50, 3), 'temp': (28.6, 1.2), 'humidity': (92.3, 1.5), 'ph': (6.3, 0.2), 'rainfall': (24, 3)},
    'apple': {'N': (20, 8), 'P': (134, 8), 'K': (199, 4), 'temp': (22.6, 1.2), 'humidity': (92.3, 1.5), 'ph': (5.9, 0.3), 'rainfall': (112, 8)},
    'orange': {'N': (19, 8), 'P': (16, 6), 'K': (10, 3), 'temp': (22.7, 8.0), 'humidity': (92.1, 1.6), 'ph': (7.0, 0.5), 'rainfall': (110, 6)},
    'papaya': {'N': (49, 11), 'P': (59, 8), 'K': (50, 3), 'temp': (33.7, 4.5), 'humidity': (92.4, 1.5), 'ph': (6.7, 0.2), 'rainfall': (142, 45)},
    'coconut': {'N': (21, 8), 'P': (16, 6), 'K': (30, 3), 'temp': (27.4, 1.2), 'humidity': (94.8, 2.5), 'ph': (5.9, 0.3), 'rainfall': (175, 30)},
    'cotton': {'N': (117, 12), 'P': (46, 8), 'K': (19, 3), 'temp': (23.9, 1.5), 'humidity': (79.8, 3.2), 'ph': (6.9, 0.5), 'rainfall': (80, 12)},
    'jute': {'N': (78, 12), 'P': (46, 8), 'K': (39, 4), 'temp': (24.9, 1.2), 'humidity': (79.6, 3.5), 'ph': (6.7, 0.4), 'rainfall': (174, 18)},
    'coffee': {'N': (101, 12), 'P': (28, 6), 'K': (29, 3), 'temp': (25.5, 1.8), 'humidity': (58.8, 4.5), 'ph': (6.7, 0.4), 'rainfall': (158, 25)},
}

def generate_crop_dataset(output_path, samples_per_crop=100):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    headers = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall', 'label']
    rows = []
    
    for crop, params in CROPS_DISTRIBUTION.items():
        for _ in range(samples_per_crop):
            # Clamp values to biologically realistic ranges
            n_val = max(0, int(round(random.gauss(params['N'][0], params['N'][1]))))
            p_val = max(5, int(round(random.gauss(params['P'][0], params['P'][1]))))
            k_val = max(5, int(round(random.gauss(params['K'][0], params['K'][1]))))
            
            temp_val = round(max(5.0, min(48.0, random.gauss(params['temp'][0], params['temp'][1]))), 2)
            hum_val = round(max(10.0, min(100.0, random.gauss(params['humidity'][0], params['humidity'][1]))), 2)
            ph_val = round(max(3.5, min(9.5, random.gauss(params['ph'][0], params['ph'][1]))), 2)
            rain_val = round(max(10.0, random.gauss(params['rainfall'][0], params['rainfall'][1])), 2)
            
            rows.append([n_val, p_val, k_val, temp_val, hum_val, ph_val, rain_val, crop])
            
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    print(f"Generated {len(rows)} samples for {len(CROPS_DISTRIBUTION)} crops at: {output_path}")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_csv = os.path.join(script_dir, 'data', 'crop_recommendation.csv')
    generate_crop_dataset(target_csv)
