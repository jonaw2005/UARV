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
// ── MAVLink command mapping ────────────────────────────────────────────────
const MAV_CMD = {
  16:  'WAYPOINT',
  17:  'LOITER_UNLIM',
  18:  'LOITER_TURNS',
  19:  'LOITER_TIME',
  20:  'RTL',
  21:  'LAND',
  22:  'TAKEOFF',
  23:  'LOITER_TO_ALT',
  24:  'DO_FOLLOW',
  30:  'CONTINUE_AND_CHANGE_ALT',
  31:  'DO_LAND_START',
  92:  'NAV_VTOL_TAKEOFF',
  93:  'DELAY',
  94:  'NAV_VTOL_LAND',
  95:  'NAV_GUIDED_ENABLE',
  96:  'NAV_GUIDED',
  112: 'DO_JUMP',
  113: 'DO_CHANGE_SPEED',
  114: 'DO_SET_HOME',
  115: 'CONDITION_YAW',
  140: 'DO_SET_SERVO',
  141: 'DO_SET_RELAY',
  176: 'DO_DIGICAM_CONFIGURE',
  177: 'DO_DIGICAM_CONTROL',
  178: 'DO_CHANGE_SPEED',
  179: 'DO_SET_CAM_TRIGG_DIST',
  180: 'DO_CHANGE_ALTITUDE',
  181: 'DO_LAND_START',
  183: 'DO_SET_ROI',
  184: 'DO_DIGICAM_CONFIGURE',
  185: 'DO_SET_CAM_TRIGG_INTERVAL',
  186: 'DO_SET_MOUNT_CONTROL',
  189: 'DO_CONTROL_VIDEO',
  190: 'DO_SET_ROI_LOCATION',
  191: 'DO_SET_ROI_SYSID',
  200: 'DO_GUIDED_CONTROL',
  300: 'DO_AUTOTUNE_ENABLE',
  400: 'NAV_PAYLOAD_PLACE',
};

const COMMAND_LABELS = {
  16:  'Waypoint',
  17:  'Loiter (Unlimited)',
  18:  'Loiter (Turns)',
  19:  'Loiter (Time)',
  20:  'Return to Launch',
  21:  'Land',
  22:  'Takeoff',
  23:  'Loiter to Alt',
  24:  'Do Follow',
  30:  'Continue & Change Alt',
  31:  'Land Start',
  92:  'VTOL Takeoff',
  93:  'Delay',
  94:  'VTOL Land',
  95:  'Guided Enable',
  96:  'Guided',
  112: 'Jump',
  113: 'Change Speed',
  114: 'Set Home',
  115: 'Condition Yaw',
  140: 'Set Servo',
  141: 'Set Relay',
  176: 'Digicam Configure',
  177: 'Digicam Control',
  178: 'Change Speed',
  179: 'Cam Trig Distance',
  180: 'Change Altitude',
  181: 'Land Start',
  183: 'Set ROI',
  184: 'Digicam Configure',
  185: 'Cam Trig Interval',
  186: 'Mount Control',
  189: 'Control Video',
  190: 'Set ROI Location',
  191: 'Set ROI SysID',
  200: 'Guided Control',
  300: 'Autotune Enable',
  400: 'Payload Place',
};

const COMMAND_ICONS = {
  16:  '📍',
  17:  '🔄',
  18:  '🔄',
  19:  '🔄',
  20:  '🏠',
  21:  '🛬',
  22:  '🛫',
  23:  '↕️',
  31:  '🛬',
  92:  '🛫',
  93:  '⏱️',
  94:  '🛬',
  112: '⤵️',
  113: '🚀',
  115: '🧭',
  140: '🔧',
  178: '🚀',
  180: '↕️',
  181: '🛬',
};

const COMMAND_BADGES = {
  16:  'badge-waypoint',
  17:  'badge-loiter',
  18:  'badge-loiter',
  19:  'badge-loiter',
  20:  'badge-rtl',
  21:  'badge-land',
  22:  'badge-takeoff',
  93:  'badge-delay',
  113: 'badge-speed',
  115: 'badge-yaw',
  178: 'badge-speed',
  180: 'badge-alt',
  181: 'badge-land',
};

const missionWindow = document.getElementById('missionWindow');
const missionContent = document.getElementById('missionContent');

function showMissionWindow(missionData) {
  if (!missionContent || !missionWindow) return;

  // The API returns a flat array directly (not wrapped in {mission: [...]})
  // Also support {mission: [...]} format in case it changes
  const items = Array.isArray(missionData) ? missionData : (missionData?.mission || []);

  if (!items || items.length === 0) {
    missionContent.innerHTML = '<div class="mission-empty">📋 Use the Mission Planner to create and upload a mission.</div>';
  } else {
    missionContent.innerHTML = items.map((item, idx) => {
      const cmd = item.command;
      const label = COMMAND_LABELS[cmd] || `Unknown (${cmd})`;
      const icon = COMMAND_ICONS[cmd] || '⚡';
      const badge = COMMAND_BADGES[cmd] || 'badge-action';

      // Convert x/y from 1e7 format to decimal degrees (only for waypoint-like commands with lat/lon)
      let lat = null;
      let lon = null;
      let alt = null;

      if (item.x !== 0 || item.y !== 0) {
        // x and y in MAVLink are int (1e7 scale for lat/lon) when frame is GLOBAL
        lat = item.x / 1e7;
        lon = item.y / 1e7;
      }
      if (item.z !== 0) {
        alt = item.z;
      }

      // Build param info string for non-waypoint commands
      let paramStr = '';
      if (cmd === 22 && item.param1 !== 0) {
        // Takeoff: param1 = min pitch, but alt is in z
        alt = item.z;
      } else if (cmd === 19) {
        // Loiter time: param1 = seconds
        if (item.param1 !== 0) paramStr = `${item.param1}s`;
      } else if (cmd === 93) {
        // Delay: param1 = seconds
        if (item.param1 !== 0) paramStr = `${item.param1}s`;
      } else if (cmd === 113 || cmd === 178) {
        // Change speed: param2 = speed, param1 = type (0=airspeed, 1=ground)
        if (item.param2 !== 0) paramStr = `${item.param2} m/s`;
      } else if (cmd === 115) {
        // Condition yaw: param1 = angle, param4 = relative (0=absolute, 1=relative)
        if (item.param1 !== 0) paramStr = `${item.param1}°`;
        if (item.param4 !== 0) paramStr += ' (relative)';
      } else if (cmd === 180) {
        // Change altitude: param1 = alt
        if (item.param1 !== 0) paramStr = `${item.param1}m`;
      } else if (cmd === 31 || cmd === 181) {
        // Land start
      } else if (cmd === 112) {
        // Jump: param1 = sequence, param2 = repeat count
        paramStr = `seq ${item.param1} × ${item.param2}`;
      } else if (cmd === 140) {
        // Set servo: param1 = servo, param2 = pwm
        paramStr = `servo ${item.param1} → ${item.param2}µs`;
      }

      // Location line
      let locationStr = '';
      if (lat && lon) {
        locationStr = `<span class="mission-coords">${lat.toFixed(6)}, ${lon.toFixed(6)}</span>`;
      }
      if (alt != null && alt !== 0) {
        const altVal = typeof alt === 'number' ? alt.toFixed(1) : alt;
        locationStr += locationStr ? ` · ${altVal}m` : `<span class="mission-alt">${altVal}m</span>`;
      }
      if (paramStr) {
        locationStr += locationStr ? ` · ${paramStr}` : `<span class="mission-param">${paramStr}</span>`;
      }

      return `
        <div class="mission-item">
          <div class="mission-item-header">
            <span class="mission-step">${icon}<span class="step-num">${idx + 1}</span></span>
            <span class="mission-type ${badge}">${label}</span>
          </div>
          ${locationStr ? `<div class="mission-location">${locationStr}</div>` : ''}
        </div>`;
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