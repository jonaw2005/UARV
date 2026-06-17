const cameraVideo = document.getElementById('cameraVideo');
const cameraStatus = document.getElementById('camera-status');
const cameraState = document.getElementById('cameraState');
const cameraOverlay = document.getElementById('cameraOverlay');
const cameraUrl = document.getElementById('cameraUrl');

const CAMERA_ENDPOINT = 'http://192.168.0.105/api/video';

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
  cameraUrl.textContent = CAMERA_ENDPOINT;
  if (!cameraVideo) {
    return;
  }

  cameraVideo.src = CAMERA_ENDPOINT;
  cameraVideo.addEventListener('loadedmetadata', () => {
    hideCameraError();
    setCameraStatus(true);
  });

  cameraVideo.addEventListener('error', () => {
    showCameraError('Could not load camera stream. Confirm the Web API endpoint is reachable.');
  });
}

window.addEventListener('DOMContentLoaded', initCameraStream);
