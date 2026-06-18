// Map functionality disabled to prevent console noise.
// This file intentionally performs no network requests or Leaflet initialization.
const mapStatus = document.getElementById('map-status');
const mapOverlay = document.getElementById('mapOverlay');

let lat = null;
let lon = null;

async function get_Location() {
  const url = 'http://192.168.0.105/api/get_telemetry';

  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Location endpoint returned ${response.status}`);
    }

    const data = await response.json();
    lat = data.lat;
    lon = data.lon;
    return { lat, lon, heading: data.heading };
  } catch (error) {
    console.error('get_Location error:', error);
    lat = null;
    lon = null;
    return { lat, lon, heading: null };
  }
}

if (mapStatus) {
  mapStatus.textContent = 'Status: Ready';
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

// ── Rotating triangle marker ───────────────────────────────────────────────

let currentHeading = 0;

const planeIcon = L.divIcon({
  className: 'plane-marker',
  html: '<div class="plane-symbol">▲</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

const planeMarker = L.marker([47.66, 9.48], { icon: planeIcon }).addTo(map);

function updateMarkerRotation(heading) {
  const el = planeMarker.getElement();
  if (!el) return;
  const symbol = el.querySelector('.plane-symbol');
  if (symbol) {
    symbol.style.transform = `rotate(${heading}deg)`;
  }
  currentHeading = heading;
}

const latitudeValue = document.getElementById('latitudeValue');
const longitudeValue = document.getElementById('longitudeValue');
const gpsUpdated = document.getElementById('gpsUpdated');

function update_Map(latValue, lonValue, heading) {
  if (!map) {
    return;
  }

  map.setView([latValue, lonValue], 15, { animate: true });
  planeMarker.setLatLng([latValue, lonValue]);
  if (heading != null) {
    updateMarkerRotation(heading);
  }
}

function updateLocationFields(latValue, lonValue) {
  if (latitudeValue) {
    latitudeValue.textContent = typeof latValue === 'number' ? latValue.toFixed(6) : '—';
  }
  if (longitudeValue) {
    longitudeValue.textContent = typeof lonValue === 'number' ? lonValue.toFixed(6) : '—';
  }
}

function updateTimestamp() {
  if (gpsUpdated) {
    gpsUpdated.textContent = new Date().toLocaleTimeString();
  }
}

const refreshLocationBtn = document.getElementById('refreshLocationBtn');
if (refreshLocationBtn) {
  refreshLocationBtn.addEventListener('click', async () => {
    console.log('Refresh Location button clicked');
    const { lat: newLat, lon: newLon, heading } = await get_Location();
    if (newLat != null && newLon != null) {
      updateLocationFields(newLat, newLon);
      update_Map(newLat, newLon, heading);
      updateTimestamp();
    }
  });
}

// ── Telemetry button ────────────────────────────────────────────────────────

const telemetryBtn = document.getElementById('telemetryBtn');
if (telemetryBtn) {
  telemetryBtn.addEventListener('click', async () => {
    const url = 'http://192.168.0.105/api/get_telemetry';
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Build a formatted list of all telemetry fields
      const lines = Object.entries(data)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([key, val]) => {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
          const value = typeof val === 'number' ? val.toFixed(4) : val;
          return `${label}: ${value}`;
        });

      if (lines.length === 0) {
        alert('No telemetry data available.');
        return;
      }

      alert(lines.join('\n'));
    } catch (err) {
      console.error('Telemetry fetch failed:', err);
      alert('Failed to fetch telemetry data.');
    }
  });
}



