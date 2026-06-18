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

function initCameraStream() {
  // Display the actual Socket.IO connection URL
  cameraUrl.textContent = window.location.origin;
  if (!cameraVideo) {
    return;
  }

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
});
