// Map functionality disabled to prevent console noise.
// This file intentionally performs no network requests or Leaflet initialization.
const mapStatus = document.getElementById('map-status');
const mapOverlay = document.getElementById('mapOverlay');

let lat = null;
let lon = null;

async function get_Location() {
  const url = 'http://192.168.0.105/api/get_location';

  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Location endpoint returned ${response.status}`);
    }

    const data = await response.json();
    lat = data.lat;
    lon = data.lon;
    return { lat, lon };
  } catch (error) {
    console.error('get_Location error:', error);
    lat = null;
    lon = null;
    return { lat, lon };
  }
}

if (mapStatus) {
  mapStatus.textContent = 'Disabled';
}

if (mapOverlay) {
  mapOverlay.textContent = 'Map is disabled.';
  mapOverlay.classList.remove('hidden');
}

const map = L.map('map').setView([47.66, 9.48], 13);

// OpenStreetMap Layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
}).addTo(map);





// If you want to re-enable the map later, restore the original map.js content.
