// Shared configuration - derives API URL from the current page origin
// so it works on any IP/domain without hardcoding.
const API_BASE = window.location.origin + '/api';