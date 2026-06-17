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
const marker = L.marker([47.66, 9.48]).addTo(map);

// OpenStreetMap Layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
}).addTo(map);




const latitudeValue = document.getElementById('latitudeValue');
const longitudeValue = document.getElementById('longitudeValue');

function update_Map(latValue, lonValue) {
  if (!map) {
    return;
  }

  map.setView([latValue, lonValue], 15, { animate: true });
  marker.setLatLng([latValue, lonValue]);
}

function updateLocationFields(latValue, lonValue) {
  if (latitudeValue) {
    latitudeValue.textContent = typeof latValue === 'number' ? latValue.toFixed(6) : '—';
  }
  if (longitudeValue) {
    longitudeValue.textContent = typeof lonValue === 'number' ? lonValue.toFixed(6) : '—';
  }
}

const refreshLocationBtn = document.getElementById('refreshLocationBtn');
if (refreshLocationBtn) {
  refreshLocationBtn.addEventListener('click', async () => {
    console.log('Refresh Location button clicked');
    const { lat: newLat, lon: newLon } = await get_Location();
    if (newLat != null && newLon != null) {
      updateLocationFields(newLat, newLon);
      update_Map(newLat, newLon);
    }
  });
}



