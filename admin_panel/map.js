const mapStatus = document.getElementById('map-status');
const mapOverlay = document.getElementById('mapOverlay');
const latitudeValue = document.getElementById('latitudeValue');
const longitudeValue = document.getElementById('longitudeValue');
const gpsUpdated = document.getElementById('gpsUpdated');

const GPS_ENDPOINT = '/api/gps';
const GPS_REFRESH_MS = 5000;

let map;
let marker;

function formatTime(date) {
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function initMap() {
  map = L.map('map', {
    zoomControl: true,
    attributionControl: false,
  }).setView([0, 0], 2);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
  }).addTo(map);

  marker = L.marker([0, 0]).addTo(map);
}

async function fetchGps() {
  try {
    const response = await fetch(GPS_ENDPOINT, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`GPS endpoint returned ${response.status}`);
    }

    const data = await response.json();
    if (typeof data.latitude !== 'number' || typeof data.longitude !== 'number') {
      throw new Error('Invalid GPS payload. Expected { latitude, longitude }.');
    }

    const { latitude, longitude } = data;
    latitudeValue.textContent = latitude.toFixed(6);
    longitudeValue.textContent = longitude.toFixed(6);
    gpsUpdated.textContent = formatTime(new Date());
    mapStatus.textContent = 'Live';
    mapOverlay.classList.add('hidden');
    map.setView([latitude, longitude], 15, { animate: true });
    marker.setLatLng([latitude, longitude]);
  } catch (error) {
    mapStatus.textContent = 'Error';
    mapOverlay.textContent = `Unable to load GPS data: ${error.message}`;
    mapOverlay.classList.remove('hidden');
    console.error('GPS fetch error:', error);
  }
}

function startGpsPolling() {
  fetchGps();
  setInterval(fetchGps, GPS_REFRESH_MS);
}

window.addEventListener('DOMContentLoaded', () => {
  initMap();
  startGpsPolling();
});
