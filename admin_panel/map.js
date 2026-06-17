// Map functionality disabled to prevent console noise.
// This file intentionally performs no network requests or Leaflet initialization.
const mapStatus = document.getElementById('map-status');
const mapOverlay = document.getElementById('mapOverlay');

if (mapStatus) {
  mapStatus.textContent = 'Disabled';
}

if (mapOverlay) {
  mapOverlay.textContent = 'Map is disabled.';
  mapOverlay.classList.remove('hidden');
}

// If you want to re-enable the map later, restore the original map.js content.
