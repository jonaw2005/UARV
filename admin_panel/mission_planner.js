const plannerMap = L.map('plannerMap').setView([47.66, 9.48], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(plannerMap);

const waypointList = document.getElementById('waypointList');
const addWaypointBtn = document.getElementById('addWaypointBtn');
const clearWaypointsBtn = document.getElementById('clearWaypointsBtn');
const uploadMissionBtn = document.getElementById('uploadMissionBtn');
const coordinateForm = document.getElementById('coordinateForm');
const inputLat = document.getElementById('inputLat');
const inputLon = document.getElementById('inputLon');
const placeWaypointBtn = document.getElementById('placeWaypointBtn');
const cancelWaypointBtn = document.getElementById('cancelWaypointBtn');

const waypoints = [];
let selectedMarker = null;

function refreshWaypointList() {
  waypointList.innerHTML = '';
  waypoints.forEach((wp, index) => {
    const row = document.createElement('div');
    row.className = 'mission-item';
    row.innerHTML = `
      <span>WP ${index + 1}: ${wp.lat.toFixed(6)}, ${wp.lon.toFixed(6)}</span>
      <button data-index="${index}">Go</button>
    `;
    row.querySelector('button').addEventListener('click', () => {
      plannerMap.setView([wp.lat, wp.lon], 16);
      selectedMarker = wp.marker;
    });
    waypointList.appendChild(row);
  });
}

function addWaypoint(lat, lon) {
  const marker = L.marker([lat, lon]).addTo(plannerMap);
  waypoints.push({ lat, lon, marker });
  refreshWaypointList();
}

plannerMap.on('click', (event) => {
  addWaypoint(event.latlng.lat, event.latlng.lng);
});

function openCoordinateForm() {
  const center = plannerMap.getCenter();
  inputLat.value = center.lat.toFixed(6);
  inputLon.value = center.lng.toFixed(6);
  coordinateForm.style.display = 'block';
}

addWaypointBtn.addEventListener('click', () => {
  openCoordinateForm();
});

placeWaypointBtn.addEventListener('click', () => {
  const lat = parseFloat(inputLat.value);
  const lon = parseFloat(inputLon.value);
  if (Number.isFinite(lat) && Number.isFinite(lon)) {
    addWaypoint(lat, lon);
    plannerMap.setView([lat, lon], 16);
    coordinateForm.style.display = 'none';
  } else {
    alert('Enter valid latitude and longitude values.');
  }
});

cancelWaypointBtn.addEventListener('click', () => {
  coordinateForm.style.display = 'none';
});

clearWaypointsBtn.addEventListener('click', () => {
  waypoints.forEach((wp) => plannerMap.removeLayer(wp.marker));
  waypoints.length = 0;
  refreshWaypointList();
});

uploadMissionBtn.addEventListener('click', () => {
  console.log('Upload mission', waypoints);
  alert(`Mission uploaded with ${waypoints.length} waypoint(s).`);
});
