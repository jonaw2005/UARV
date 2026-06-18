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

// ── Generic drag logic for floating windows ─────────────────────────────────

function makeDraggable(windowEl) {
  if (!windowEl) return;
  const handle = windowEl.querySelector('[data-drag-handle]');
  if (!handle) return;

  let isDragging = false;
  let offsetX = 0;
  let offsetY = 0;

  function onStart(e) {
    isDragging = true;
    const cx = e.clientX ?? e.touches?.[0]?.clientX;
    const cy = e.clientY ?? e.touches?.[0]?.clientY;
    const rect = windowEl.getBoundingClientRect();
    offsetX = cx - rect.left;
    offsetY = cy - rect.top;
    windowEl.style.left = rect.left + 'px';
    windowEl.style.top = rect.top + 'px';
    windowEl.style.right = 'auto';
    e.preventDefault();
  }

  function onMove(e) {
    if (!isDragging) return;
    const cx = e.clientX ?? e.touches?.[0]?.clientX;
    const cy = e.clientY ?? e.touches?.[0]?.clientY;
    if (cx == null || cy == null) return;
    windowEl.style.left = (cx - offsetX) + 'px';
    windowEl.style.top = (cy - offsetY) + 'px';
    e.preventDefault();
  }

  function onEnd() {
    isDragging = false;
  }

  handle.addEventListener('mousedown', onStart);
  handle.addEventListener('touchstart', onStart, { passive: false });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('touchmove', onMove, { passive: false });
  document.addEventListener('mouseup', onEnd);
  document.addEventListener('touchend', onEnd);
}

function showDragWindow(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}

function hideDragWindow(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

// Wire close buttons
document.querySelectorAll('[data-close-btn]').forEach((btn) => {
  const win = btn.closest('.drag-window');
  if (!win) return;
  btn.addEventListener('click', () => win.classList.add('hidden'));
});

// Make all existing drag windows draggable
document.querySelectorAll('.drag-window').forEach(makeDraggable);

// ── Telemetry button ────────────────────────────────────────────────────────

const telemetryWindow = document.getElementById('telemetryWindow');
const telemetryContent = document.getElementById('telemetryContent');

function showTelemetryWindow(data) {
  if (!telemetryContent || !telemetryWindow) return;

  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) {
    telemetryContent.innerHTML = '<p style="color: #a8b2c7; text-align: center;">No telemetry data available.</p>';
  } else {
    telemetryContent.innerHTML = entries.map(([key, val]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      const value = typeof val === 'number' ? val.toFixed(4) : val;
      return `<div class="drag-row"><span class="label">${label}</span><span class="value">${value}</span></div>`;
    }).join('');
  }

  showDragWindow('telemetryWindow');
}

const telemetryBtn = document.getElementById('telemetryBtn');
if (telemetryBtn) {
  telemetryBtn.addEventListener('click', async () => {
    const url = 'http://192.168.0.105/api/get_telemetry';
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      showTelemetryWindow(data);
    } catch (err) {
      console.error('Telemetry fetch failed:', err);
      if (telemetryContent) {
        telemetryContent.innerHTML = '<p style="color: #e06c75; text-align: center;">Failed to fetch telemetry data.</p>';
      }
      showDragWindow('telemetryWindow');
    }
  });
}

// ── Mission Order button ────────────────────────────────────────────────────

const missionWindow = document.getElementById('missionWindow');
const missionContent = document.getElementById('missionContent');

function showMissionWindow(missionData) {
  if (!missionContent || !missionWindow) return;

  const items = missionData?.mission;
  if (!items || items.length === 0) {
    missionContent.innerHTML = '<p style="color: #a8b2c7; text-align: center; padding: 12px 0;">Use the Mission Planner to create and upload a mission.</p>';
  } else {
    missionContent.innerHTML = items.map((item, idx) => {
      const type = item.type || 'unknown';
      const details = item.action || item.lat || '';
      const lat = item.lat ? item.lat.toFixed(6) : '';
      const lon = item.lon ? item.lon.toFixed(6) : '';
      const alt = item.alt || item.param || '';
      let info = type;
      if (lat && lon) info += ` · ${lat}, ${lon}`;
      if (alt) info += ` · ${alt}m`;
      return `<div class="drag-row"><span class="label">#${idx + 1}</span><span class="value">${info}</span></div>`;
    }).join('');
  }

  showDragWindow('missionWindow');
}

const downloadMissionBtn = document.getElementById('downloadMissionBtn');
if (downloadMissionBtn) {
  downloadMissionBtn.addEventListener('click', async () => {
    const url = 'http://192.168.0.105/api/mission_download';
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      showMissionWindow(data);
    } catch (err) {
      console.error('Mission download failed:', err);
      if (missionContent) {
        missionContent.innerHTML = '<p style="color: #e06c75; text-align: center;">Failed to download mission.</p>';
      }
      showDragWindow('missionWindow');
    }
  });
}