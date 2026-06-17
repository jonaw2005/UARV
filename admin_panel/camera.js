const cameraVideo = document.getElementById('cameraVideo');
const cameraStatus = document.getElementById('camera-status');
const cameraState = document.getElementById('cameraState');
const cameraOverlay = document.getElementById('cameraOverlay');
const cameraUrl = document.getElementById('cameraUrl');

const SOCKET_SERVER = 'http://182.168.0.105:5000';

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
  cameraUrl.textContent = SOCKET_SERVER;
  if (!cameraVideo) {
    return;
  }

  const socket = io(SOCKET_SERVER, { transports: ['websocket'] });

  socket.on('connect', () => {
    hideCameraError();
    setCameraStatus(true);
  });

  socket.on('disconnect', () => {
    showCameraError('Socket.IO disconnected.');
  });

  socket.on('connect_error', (error) => {
    showCameraError('Could not connect to Socket.IO.');
    console.error('Socket.IO connect error:', error);
  });

  socket.on('video_frame', (data) => {
    if (data && data.image) {
      cameraVideo.src = data.image;
    }
  });
}

window.addEventListener('DOMContentLoaded', initCameraStream);
