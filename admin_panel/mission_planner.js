const plannerMap = L.map('plannerMap').setView([47.66, 9.48], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(plannerMap);

const waypointList = document.getElementById('waypointList');
const missionList = document.getElementById('missionList');
const addWaypointBtn = document.getElementById('addWaypointBtn');
const addActionBtn = document.getElementById('addActionBtn');
const clearWaypointsBtn = document.getElementById('clearWaypointsBtn');
const uploadMissionBtn = document.getElementById('uploadMissionBtn');
const coordinateForm = document.getElementById('coordinateForm');
const inputLat = document.getElementById('inputLat');
const inputLon = document.getElementById('inputLon');
const placeWaypointBtn = document.getElementById('placeWaypointBtn');
const cancelWaypointBtn = document.getElementById('cancelWaypointBtn');
const actionForm = document.getElementById('actionForm');
const actionType = document.getElementById('actionType');
const actionParam = document.getElementById('actionParam');
const actionParamLabel = document.getElementById('actionParamLabel');
const placeActionBtn = document.getElementById('placeActionBtn');
const cancelActionBtn = document.getElementById('cancelActionBtn');

const waypoints = [];
const missionItems = [];
let selectedMarker = null;
let editingIndex = null;
let missionPolyline = null;

function createNumberedMarker(lat, lon, number) {
  const icon = L.divIcon({
    className: 'mission-waypoint-marker',
    html: `<div class="marker-number">${number}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
  return L.marker([lat, lon], { icon });
}

function updateMissionPolyline() {
  if (missionPolyline) {
    plannerMap.removeLayer(missionPolyline);
    missionPolyline = null;
  }

  const waypointCoords = missionItems
    .filter((item) => item.type === 'waypoint')
    .map((item) => [item.lat, item.lon]);

  if (waypointCoords.length > 1) {
    missionPolyline = L.polyline(waypointCoords, {
      color: '#ff3333',
      weight: 2,
      opacity: 0.7,
    }).addTo(plannerMap);
  }
}

function refreshMissionList() {
  missionList.innerHTML = '';
  if (!missionItems.length) {
    missionList.innerHTML = '<div class="mission-item">No mission items yet.</div>';
    return;
  }

  missionItems.forEach((item, index) => {
    const row = document.createElement('div');
    row.className = 'mission-item';
    row.draggable = true;
    row.dataset.index = index;
    row.innerHTML = `
      <span>${index + 1}. ${item.title}</span>
      <div class="mission-item-buttons">
        <button data-index="${index}" class="edit-btn">Edit</button>
        <button data-index="${index}" class="remove-btn">Remove</button>
      </div>
    `;
    row.querySelector('.edit-btn').addEventListener('click', () => {
      editingIndex = index;
      if (item.type === 'waypoint') {
        inputLat.value = item.lat.toFixed(6);
        inputLon.value = item.lon.toFixed(6);
        coordinateForm.style.display = 'block';
        actionForm.style.display = 'none';
      } else if (item.type === 'action') {
        actionType.value = item.action;
        updateActionFields();
        actionParam.value = item.param || '';
        actionForm.style.display = 'block';
        coordinateForm.style.display = 'none';
      }
    });
    row.querySelector('.remove-btn').addEventListener('click', () => {
      // Remove marker from map if it exists
      if (item.missionMarker) {
        plannerMap.removeLayer(item.missionMarker);
      }
      // Remove from waypoints array if it's a waypoint
      if (item.type === 'waypoint') {
        const wpIndex = waypoints.findIndex(wp => wp.lat === item.lat && wp.lon === item.lon);
        if (wpIndex !== -1) {
          waypoints.splice(wpIndex, 1);
        }
      }
      missionItems.splice(index, 1);
      refreshMissionList();
      refreshWaypointList();
    });
    setupMissionDragEvents(row);
    missionList.appendChild(row);
  });

  updateMissionMarkersAndPolyline();
}

function updateMissionMarkersAndPolyline() {
  // Clear old mission markers
  missionItems.forEach((item) => {
    if (item.missionMarker) {
      plannerMap.removeLayer(item.missionMarker);
    }
  });

  // Create new numbered markers
  let waypointCount = 1;
  missionItems.forEach((item) => {
    if (item.type === 'waypoint') {
      const marker = createNumberedMarker(item.lat, item.lon, waypointCount);
      marker.addTo(plannerMap);
      item.missionMarker = marker;
      waypointCount++;
    }
  });

  // Update polyline
  updateMissionPolyline();
}

function moveMissionItem(fromIndex, toIndex) {
  if (fromIndex === toIndex) return;
  const [moved] = missionItems.splice(fromIndex, 1);
  missionItems.splice(toIndex, 0, moved);
  refreshMissionList();
}

function setupMissionDragEvents(row) {
  row.addEventListener('dragstart', (event) => {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', row.dataset.index);
    row.classList.add('dragging');
  });

  row.addEventListener('dragover', (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    row.classList.add('drag-over');
  });

  row.addEventListener('dragenter', (event) => {
    event.preventDefault();
    row.classList.add('drag-over');
  });

  row.addEventListener('dragleave', () => {
    row.classList.remove('drag-over');
  });

  row.addEventListener('drop', (event) => {
    event.preventDefault();
    const fromIndex = Number(event.dataTransfer.getData('text/plain'));
    const toIndex = Number(row.dataset.index);
    row.classList.remove('drag-over');
    moveMissionItem(fromIndex, toIndex);
  });

  row.addEventListener('dragend', () => {
    row.classList.remove('dragging');
    document.querySelectorAll('.mission-item.drag-over').forEach((item) => {
      item.classList.remove('drag-over');
    });
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
  const waypoint = { lat, lon };
  waypoints.push(waypoint);
  missionItems.push({
    type: 'waypoint',
    title: `Waypoint ${missionItems.filter((item) => item.type === 'waypoint').length + 1}: ${lat.toFixed(6)}, ${lon.toFixed(6)}`,
    lat,
    lon,
  });
  refreshWaypointList();
  refreshMissionList();
}

plannerMap.on('click', (event) => {
  addWaypoint(event.latlng.lat, event.latlng.lng);
});

function openCoordinateForm() {
  if (editingIndex === null) {
    const center = plannerMap.getCenter();
    inputLat.value = center.lat.toFixed(6);
    inputLon.value = center.lng.toFixed(6);
  }
  coordinateForm.style.display = 'block';
  actionForm.style.display = 'none';
}

function openActionForm() {
  if (editingIndex === null) {
    actionType.value = 'takeoff';
  }
  updateActionFields();
  actionForm.style.display = 'block';
  coordinateForm.style.display = 'none';
}

function updateActionFields() {
  const action = actionType.value;
  let label = 'Parameter';
  let placeholder = '';
  let step = '1';

  switch (action) {
    case 'takeoff':
      label = 'Takeoff altitude (m)';
      placeholder = '100';
      break;
    case 'loiter':
      label = 'Loiter time (s)';
      placeholder = '60';
      break;
    case 'rtl':
      label = 'No parameters';
      placeholder = '';
      break;
    case 'land':
      label = 'No parameters';
      placeholder = '';
      break;
    case 'delay':
      label = 'Delay seconds';
      placeholder = '10';
      break;
    case 'set_speed':
      label = 'Speed (m/s)';
      placeholder = '15';
      break;
    case 'condition_yaw':
      label = 'Yaw heading (deg)';
      placeholder = '90';
      break;
    case 'land_start':
      label = 'No parameters';
      placeholder = '';
      break;
    default:
      label = 'Parameter';
      placeholder = '';
  }

  actionParamLabel.querySelector('.param-label').textContent = label;
  actionParam.placeholder = placeholder;
  actionParam.step = step;
  actionParam.value = '';
  actionParam.disabled = action === 'rtl' || action === 'land' || action === 'land_start';
  actionParam.style.display = action === 'rtl' || action === 'land' || action === 'land_start' ? 'none' : 'block';
  actionParamLabel.style.display = action === 'rtl' || action === 'land' || action === 'land_start' ? 'none' : 'grid';
}

addWaypointBtn.addEventListener('click', () => {
  openCoordinateForm();
});

addActionBtn.addEventListener('click', () => {
  openActionForm();
});

placeWaypointBtn.addEventListener('click', () => {
  const lat = parseFloat(inputLat.value);
  const lon = parseFloat(inputLon.value);
  if (Number.isFinite(lat) && Number.isFinite(lon)) {
    if (editingIndex !== null) {
      // Update existing waypoint
      const item = missionItems[editingIndex];
      item.lat = lat;
      item.lon = lon;
      item.title = `Waypoint ${editingIndex + 1}: ${lat.toFixed(6)}, ${lon.toFixed(6)}`;
      editingIndex = null;
    } else {
      // Create new waypoint
      addWaypoint(lat, lon);
    }
    plannerMap.setView([lat, lon], 16);
    coordinateForm.style.display = 'none';
    refreshWaypointList();
    refreshMissionList();
  } else {
    alert('Enter valid latitude and longitude values.');
  }
});

placeActionBtn.addEventListener('click', () => {
  const action = actionType.value;
  const param = actionParam.value;
  const titleMap = {
    takeoff: `Takeoff to ${param || 'auto'} m`,
    loiter: `Loiter for ${param || '0'} s`,
    rtl: 'Return to Launch',
    land: 'Land',
    delay: `Delay ${param || '0'} s`,
    set_speed: `Set speed to ${param || '0'} m/s`,
    condition_yaw: `Condition yaw to ${param || '0'}°`,
  };

  if (editingIndex !== null) {
    // Update existing action
    const item = missionItems[editingIndex];
    item.action = action;
    item.param = param;
    item.title = titleMap[action] || 'Action';
    editingIndex = null;
  } else {
    // Create new action
    const center = plannerMap.getCenter();
    missionItems.push({
      type: 'action',
      title: titleMap[action] || 'Action',
      action,
      param,
      lat: center.lat,
      lon: center.lng,
    });
  }
  refreshMissionList();
  actionForm.style.display = 'none';
});

actionType.addEventListener('change', updateActionFields);

cancelWaypointBtn.addEventListener('click', () => {
  editingIndex = null;
  coordinateForm.style.display = 'none';
});

cancelActionBtn.addEventListener('click', () => {
  editingIndex = null;
  actionForm.style.display = 'none';
});

clearWaypointsBtn.addEventListener('click', () => {
  // Remove all mission markers from map
  missionItems.forEach((item) => {
    if (item.missionMarker) {
      plannerMap.removeLayer(item.missionMarker);
    }
  });
  
  // Clear polyline
  if (missionPolyline) {
    plannerMap.removeLayer(missionPolyline);
    missionPolyline = null;
  }
  
  // Clear data
  waypoints.length = 0;
  missionItems.length = 0;
  refreshWaypointList();
  refreshMissionList();
});

function missionToMAVLink(missionJson) {
    const MAV_CMD = {
        waypoint: 16,          // NAV_WAYPOINT
        takeoff: 22,           // NAV_TAKEOFF
        loiter: 19,            // NAV_LOITER_TIME
        rtl: 20,               // NAV_RETURN_TO_LAUNCH
        land: 21,              // NAV_LAND
        delay: 93,             // NAV_DELAY
        set_speed: 178,        // DO_CHANGE_SPEED
        condition_yaw: 115,    // CONDITION_YAW
        land_start: 21         // treat as land
    };

    const frame = 6; // MAV_FRAME_GLOBAL_RELATIVE_ALT_INT

    return missionJson.mission.map((item, index) => {

        let cmd = MAV_CMD[item.action] || 16;

        let missionItem = {
            seq: item.seq ?? index,
            frame: frame,
            command: cmd,

            current: 0,
            autocontinue: 1,

            param1: 0,
            param2: 0,
            param3: 0,
            param4: 0,

            x: 0,
            y: 0,
            z: 0
        };

        switch (item.type) {

            case "waypoint":
                missionItem.x = Math.floor(item.lat * 1e7);
                missionItem.y = Math.floor(item.lon * 1e7);
                missionItem.z = 20; // default altitude or extend schema
                break;

            case "action":
                switch (item.action) {

                    case "takeoff":
                        missionItem.param7 = parseFloat(item.param || 10);
                        break;

                    case "loiter":
                        missionItem.param1 = parseFloat(item.param || 60);
                        break;

                    case "delay":
                        missionItem.param1 = parseFloat(item.param || 0);
                        break;

                    case "set_speed":
                        missionItem.param1 = 1; // ground speed
                        missionItem.param2 = parseFloat(item.param || 5);
                        break;

                    case "condition_yaw":
                        missionItem.param1 = parseFloat(item.param || 0);
                        missionItem.param2 = 0;
                        missionItem.param3 = 1; // direction
                        missionItem.param4 = 0;
                        break;

                    case "rtl":
                    case "land":
                    case "land_start":
                        // no params needed
                        break;
                }
                break;
        }

        return missionItem;
    });
}


function exportMissionToJSON() {
  const missionJSON = {
    mission: []
  };

  missionItems.forEach((item, index) => {
    const seq = index;  // 0-based seq — matches MAVLink MISSION_REQUEST seq
    if (item.type === 'waypoint') {
      missionJSON.mission.push({
        type: 'waypoint',
        seq: seq,
        lat: item.lat,
        lon: item.lon
      });
    } else if (item.type === 'action') {
      const entry = {
        type: 'action',
        seq: seq,
        action: item.action
      };
      // Only include param if the action has one (not rtl, land, or land_start)
      if (item.param && item.param !== '' && !['rtl', 'land', 'land_start'].includes(item.action)) {
        entry.param = item.param;
      }
      missionJSON.mission.push(entry);
    }
  });

  return missionJSON;
}

uploadMissionBtn.addEventListener('click', async () => {
  const missionJSON = missionToMAVLink(exportMissionToJSON());
  //console.log('Mission JSON:', JSON.stringify(missionJSON, null, 2));
  console.log('Mission JSON:', JSON.stringify(missionJSON));
  try {
    const response = await fetch('http://192.168.0.105/api/mission_upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(missionJSON),
    });
    const result = await response.json();
    if (response.ok) {
      alert(`Mission uploaded successfully with ${missionItems.length} item(s).`);
    } else {
      alert(`Upload failed: ${result.error || response.status}`);
    }
  } catch (error) {
    alert(`Upload failed: ${error.message}`);
  }
});


function loadMissionFromJSON(missionData) {
  // Clear existing mission
  missionItems.forEach((item) => {
    if (item.missionMarker) {
      plannerMap.removeLayer(item.missionMarker);
    }
  });
  if (missionPolyline) {
    plannerMap.removeLayer(missionPolyline);
    missionPolyline = null;
  }
  waypoints.length = 0;
  missionItems.length = 0;

  // Load items from downloaded mission
  const actionTitleMap = {
    takeoff: (p) => `Takeoff to ${p || 'auto'} m`,
    loiter: (p) => `Loiter for ${p || '0'} s`,
    rtl: () => 'Return to Launch',
    land: () => 'Land',
    delay: (p) => `Delay ${p || '0'} s`,
    set_speed: (p) => `Set speed to ${p || '0'} m/s`,
    condition_yaw: (p) => `Condition yaw to ${p || '0'}°`,
    land_start: () => 'Land Start',
  };

  missionData.forEach((item) => {
    if (item.type === 'waypoint') {
      const wp = { lat: item.lat, lon: item.lon };
      waypoints.push(wp);
      missionItems.push({
        type: 'waypoint',
        title: `Waypoint ${missionItems.filter(i => i.type === 'waypoint').length + 1}: ${item.lat.toFixed(6)}, ${item.lon.toFixed(6)}`,
        lat: item.lat,
        lon: item.lon,
      });
    } else if (item.type === 'action') {
      const param = item.param || '';
      const titleFn = actionTitleMap[item.action] || (() => 'Action');
      missionItems.push({
        type: 'action',
        title: titleFn(param),
        action: item.action,
        param: param,
        lat: item.lat || 0,
        lon: item.lon || 0,
      });
    }
  });

  refreshWaypointList();
  refreshMissionList();
}


async function downloadMission() {
  try {
    const response = await fetch('http://192.168.0.105/api/mission_download');
    if (!response.ok) {
      alert(`Download failed with status ${response.status}`);
      return;
    }
    const result = await response.json();
    if (result.mission && result.mission.length > 0) {
      loadMissionFromJSON(result.mission);
      alert(`Mission downloaded: ${result.mission.length} item(s).`);
    } else {
      alert('No mission items on Pixhawk.');
    }
  } catch (error) {
    alert(`Download failed: ${error.message}`);
  }
}

refreshWaypointList();
refreshMissionList();
