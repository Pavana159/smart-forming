/**
 * Smart Farming AI - Frontend JavaScript Module
 * Handles client-side interactivity, geolocation, image upload previews,
 * Chart.js visualizations, and asynchronous API calls.
 */

document.addEventListener('DOMContentLoaded', () => {
    initImageUploadPreviews();
    initNotificationBadges();
});

// -------------------------------------------------------------
// 1. Image Upload Preview & Drag-and-Drop Handler
// -------------------------------------------------------------
function initImageUploadPreviews() {
    const dropzones = document.querySelectorAll('.dropzone-box');
    
    dropzones.forEach(zone => {
        const fileInput = zone.querySelector('input[type="file"]');
        const previewContainer = zone.querySelector('.image-preview-container');
        const previewImg = zone.querySelector('.preview-image');
        const placeholder = zone.querySelector('.dropzone-placeholder');
        const retakeBtn = zone.querySelector('.btn-retake');

        if (!fileInput) return;

        // Click to open file dialog
        zone.addEventListener('click', (e) => {
            if (e.target !== retakeBtn && !retakeBtn?.contains(e.target)) {
                fileInput.click();
            }
        });

        // Drag & Drop effects
        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove('dragover');
            });
        });

        zone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                showPreview(files[0], previewContainer, previewImg, placeholder);
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                showPreview(fileInput.files[0], previewContainer, previewImg, placeholder);
            }
        });

        if (retakeBtn) {
            retakeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                fileInput.value = '';
                if (previewContainer) previewContainer.classList.add('d-none');
                if (placeholder) placeholder.classList.remove('d-none');
            });
        }
    });
}

function showPreview(file, container, imgElem, placeholder) {
    if (!file || !file.type.startsWith('image/')) {
        alert("Please select a valid image file (JPEG, PNG, WebP).");
        return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
        if (imgElem) imgElem.src = e.target.result;
        if (container) container.classList.remove('d-none');
        if (placeholder) placeholder.classList.add('d-none');
    };
    reader.readAsDataURL(file);
}

// -------------------------------------------------------------
// 2. Geolocation & Weather Helper
// -------------------------------------------------------------
function detectBrowserLocation(onSuccess, onError) {
    if (!navigator.geolocation) {
        if (onError) onError("Geolocation is not supported by your browser.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            if (onSuccess) onSuccess(lat, lon);
        },
        (error) => {
            let message = "Unable to retrieve GPS coordinates.";
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    message = "Location permission denied. Please enter your farm location manually.";
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = "Location information is unavailable.";
                    break;
                case error.TIMEOUT:
                    message = "Location request timed out.";
                    break;
            }
            if (onError) onError(message);
        },
        { timeout: 10000, enableHighAccuracy: true }
    );
}

// -------------------------------------------------------------
// 3. Chart.js Renderers
// -------------------------------------------------------------

function renderWeatherChart(canvasId, forecastDays) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart || !forecastDays || forecastDays.length === 0) return;

    const labels = forecastDays.map(d => `${d.day_name} (${d.date.slice(5)})`);
    const maxTemps = forecastDays.map(d => d.temp_max);
    const minTemps = forecastDays.map(d => d.temp_min);
    const rainSums = forecastDays.map(d => d.rain_sum);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Max Temp (°C)',
                    data: maxTemps,
                    borderColor: '#e76f51',
                    backgroundColor: 'rgba(231, 111, 81, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Min Temp (°C)',
                    data: minTemps,
                    borderColor: '#2a9d8f',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [4, 4],
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    type: 'bar',
                    label: 'Rainfall (mm)',
                    data: rainSums,
                    backgroundColor: 'rgba(56, 189, 248, 0.65)',
                    borderRadius: 6,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Temperature (°C)', color: '#1b4332' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Rainfall (mm)', color: '#0284c7' },
                    min: 0
                }
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: { padding: 10, cornerRadius: 8 }
            }
        }
    });
}

function renderCropHealthChart(canvasId, historyData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart || !historyData || historyData.length === 0) return;

    const labels = historyData.map(h => `${h.observation_date} (${h.growth_stage.split(' ')[0]})`);
    const canopy = historyData.map(h => h.canopy_coverage);
    const chlorosis = historyData.map(h => h.chlorosis_yellowing);
    const necrosis = historyData.map(h => h.necrosis_spots);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Canopy Density (%)',
                    data: canopy,
                    borderColor: '#2d6a4f',
                    backgroundColor: 'rgba(45, 106, 79, 0.12)',
                    fill: true,
                    borderWidth: 3,
                    tension: 0.3
                },
                {
                    label: 'Yellowing / Chlorosis (%)',
                    data: chlorosis,
                    borderColor: '#eab308',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    tension: 0.2
                },
                {
                    label: 'Necrosis / Leaf Spots (%)',
                    data: necrosis,
                    borderColor: '#ef4444',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    title: { display: true, text: 'Foliage Metric (%)' }
                }
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: { padding: 10, cornerRadius: 8 }
            }
        }
    });
}

// -------------------------------------------------------------
// 4. Notifications Fetcher
// -------------------------------------------------------------
function initNotificationBadges() {
    // Optional polling or initial check
}
