const cameraVideo = document.getElementById('cameraVideo');
const cameraStatus = document.getElementById('camera-status');
const cameraState = document.getElementById('cameraState');
const cameraOverlay = document.getElementById('cameraOverlay');
const cameraUrl = document.getElementById('cameraUrl');

const SOCKET_SERVER = 'http://192.168.0.105:5000';

function setCameraStatus(connected) {
  cameraStatus.textContent = connected ? 'Live' : 'Offline';
  cameraState.textContent = connected ? 'Connected' : 'Disconnected';
}

function showCameraError(message) {
  cameraOverlay.textContent = message;
  cameraOverlay.classList.remove('hidden');
  setCameraStatus(false);
}

function hideCameraError() {
  cameraOverlay.classList.add('hidden');
}

function switch_NV_mode() {
  console.log('Switch NV Mode triggered');
  const API_BASE = 'http://192.168.0.105:8000';
  fetch(`${API_BASE}/switch_nv_mode`, { method: 'POST' })
    .then(res => res.json())
    .then(data => console.log('NV mode response:', data))
    .catch(err => console.error('NV mode request failed:', err));
}

function initCameraStream() {
  cameraUrl.textContent = SOCKET_SERVER;
  if (!cameraVideo) {
    return;
  }
  /**
  const socket = io(window.location.origin, {
    path: "/socket.io",
    transports: ['websocket']
  });
  **/

  const socket  = io(window.location.origin)

  socket.on('connect', () => {
    hideCameraError();
    setCameraStatus(true);
    console.log("Socket connected:", socket.id);
  });

  socket.on('disconnect', () => {
    showCameraError('Socket.IO disconnected.');
  });

  socket.on('connect_error', (error) => {
    showCameraError('Could not connect to Socket.IO.');
    console.error('Socket.IO connect error:', error);
  });

  socket.on('video_frame', (data) => {

    const frame = data?.image || data;

    if (!frame) return;

    /**
     * Unterstützt beide Varianten:
     * 1) data.image (dein bisheriger Ansatz)
     * 2) direkt base64 string (empfohlen)
     */

    //const frame = data.image || data;

    /*if (typeof frame === "string") {
      cameraVideo.src = frame; 
    }*/
    cameraVideo.src = "data:image/jpeg;base64," + frame;
  });
}

window.addEventListener('DOMContentLoaded', () => {
  initCameraStream();

  const nvBtn = document.getElementById('nvModeBtn');
  if (nvBtn) {
    nvBtn.addEventListener('click', switch_NV_mode);
  }
});
