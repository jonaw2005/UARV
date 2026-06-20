const actionButtons = Array.from(document.querySelectorAll('.action-btn'));

// ── API helper ──────────────────────────────────────────────────────────────
// API_BASE is defined in config.js (loaded before this file)

async function apiPost(endpoint, body = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API POST ${endpoint} failed:`, err);
  }
}

async function apiGet(endpoint) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API GET ${endpoint} failed:`, err);
  }
}

async function apiGetText(endpoint) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`API GET ${endpoint} failed:`, err);
  }
}

// ── Command functions (exported for use by HTML) ────────────────────────────

function arm_disarm() {
  console.log('Arm / Disarm triggered');
  apiGet('/arm_disarm');
}

function change_Mode(mode) {
  console.log(`Change mode to: ${mode}`);
  apiPost('/change_flightmode', { mode });
}

function takeoff() {
  console.log('Takeoff triggered');
  apiGet('/takeoff');
}

function abort_mission() {
  console.log('Abort mission triggered');
  apiGet('/abort_mission');
}

// ── Mode dropdown UI ────────────────────────────────────────────────────────

const MODES = ['MANUAL', 'FBWA', 'AUTO', 'GUIDED', 'RTL', 'LOITER', 'STABILIZE', 'AUTOLAND', 'LAND'];

function buildModeDropdown(modeButton) {
  const wrapper = document.createElement('div');
  wrapper.className = 'mode-dropdown-wrapper';
  wrapper.style.position = 'relative';

  const dropdown = document.createElement('div');
  dropdown.className = 'mode-dropdown';
  dropdown.style.cssText = `
    display: none;
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    background: rgba(14, 28, 39, 0.98);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 4px;
  `;

  MODES.forEach((mode) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.textContent = mode;
    item.style.cssText = `
      display: block;
      width: 100%;
      padding: 12px 16px;
      border: none;
      background: transparent;
      color: #edf2f7;
      font-size: 0.95rem;
      cursor: pointer;
      text-align: left;
      transition: background 0.12s;
    `;
    item.addEventListener('mouseenter', () => {
      item.style.background = 'rgba(45, 107, 255, 0.25)';
    });
    item.addEventListener('mouseleave', () => {
      item.style.background = 'transparent';
    });
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      change_Mode(mode);
      modeButton.textContent = `Mode: ${mode}`;
      dropdown.style.display = 'none';
    });
    dropdown.appendChild(item);
  });

  wrapper.appendChild(dropdown);
  return { wrapper, dropdown };
}

// ── Arm status polling ─────────────────────────────────────────────────────

let armPollInterval = null;

async function _fetchArmStatus() {
  const res = await fetch(`${API_BASE}/is_armed`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  return text.trim();
}

function startArmStatusPoll() {
  const armBtn = document.getElementById('armDisarmBtn');
  if (!armBtn) return;
  const statusSpan = armBtn.querySelector('.btn-sub-text');

  async function poll() {
    try {
      const text = await _fetchArmStatus();
      if (text === 'True' || text === 'true') {
        statusSpan.textContent = 'Status: ✅ ARMED';
      } else if (text === 'False' || text === 'false') {
        statusSpan.textContent = 'Status: ⛔ DISARMED';
      } else {
        statusSpan.textContent = 'Status: Error';
      }
    } catch {
      statusSpan.textContent = 'Status: Unreachable';
    }
  }

  // Poll every 3 seconds
  poll();
  armPollInterval = setInterval(poll, 3000);
}

function stopArmStatusPoll() {
  if (armPollInterval) {
    clearInterval(armPollInterval);
    armPollInterval = null;
  }
}

// ── Button setup ────────────────────────────────────────────────────────────

function setupActionButtons() {
  const buttons = document.querySelectorAll('.action-btn');
  if (buttons.length < 4) return;

  // Arm / Disarm
  buttons[0].disabled = false;
  buttons[0].id = 'armDisarmBtn';
  buttons[0].addEventListener('click', arm_disarm);

  // Mode Selection
  buttons[1].disabled = false;
  buttons[1].id = 'modeSelectBtn';
  const { wrapper, dropdown } = buildModeDropdown(buttons[1]);
  // Insert the wrapper after the button in the DOM
  buttons[1].parentNode.insertBefore(wrapper, buttons[1].nextSibling);
  wrapper.appendChild(buttons[1]); // move button into wrapper

  buttons[1].addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', () => {
    dropdown.style.display = 'none';
  });

  // Mission Start
  buttons[2].disabled = false;
  buttons[2].id = 'takeoffBtn';
  buttons[2].addEventListener('click', takeoff);

  // ABORT
  buttons[3].disabled = false;
  buttons[3].id = 'abortBtn';
  buttons[3].addEventListener('click', abort_mission);

  // Start arm status polling every 3 seconds
  startArmStatusPoll();
}

window.addEventListener('DOMContentLoaded', setupActionButtons);