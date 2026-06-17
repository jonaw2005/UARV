const plannerMap = L.map('plannerMap').setView([47.66, 9.48], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(plannerMap);

const waypointList = document.getElementById('waypointList');
const missionList = document.getElementById('missionList');
const addWaypointBtn = document.getElementById('addWaypointBtn');
const clearWaypointsBtn = document.getElementById('clearWaypointsBtn');
const uploadMissionBtn = document.getElementById('uploadMissionBtn');
const coordinateForm = document.getElementById('coordinateForm');
const inputLat = document.getElementById('inputLat');
const inputLon = document.getElementById('inputLon');
const placeWaypointBtn = document.getElementById('placeWaypointBtn');
const cancelWaypointBtn = document.getElementById('cancelWaypointBtn');

const waypoints = [];
const missionItems = [];
let selectedMarker = null;

function refreshMissionList() {
  missionList.innerHTML = '';
  if (!missionItems.length) {
    missionList.innerHTML = '<div class="mission-item">No mission items yet.</div>';
    return;
  }

  missionItems.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'mission-item';
    row.innerHTML = `
      <span>${index + 1}. ${item.title}</span>
      <button data-index="${index}">Go</button>
    `;
    row.querySelector('button').addEventListener('click', () => {
      plannerMap.setView([item.lat, item.lon], 16);
      selectedMarker = item.marker;
    });
    missionList.appendChild(row);
  });
}

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
  const waypoint = { lat, lon, marker };
  waypoints.push(waypoint);
  missionItems.push({
    type: 'waypoint',
    title: `Waypoint ${missionItems.length + 1}: ${lat.toFixed(6)}, ${lon.toFixed(6)}`,
    lat,
    lon,
    marker,
  });
  refreshWaypointList();
  refreshMissionList();
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
  missionItems.length = 0;
  refreshWaypointList();
  refreshMissionList();
});

uploadMissionBtn.addEventListener('click', () => {
  console.log('Upload mission', missionItems);
  alert(`Mission uploaded with ${missionItems.length} waypoint(s).`);
});

refreshWaypointList();
refreshMissionList();
