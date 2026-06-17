const actionButtons = Array.from(document.querySelectorAll('.action-btn'));

// ── API helper ──────────────────────────────────────────────────────────────
const API_BASE = 'http://192.168.0.105:5000';

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

// ── Command functions (exported for use by HTML) ────────────────────────────

function arm_disarm() {
  console.log('Arm / Disarm triggered');
  apiPost('/api/arm_disarm');
}

function change_Mode(mode) {
  console.log(`Change mode to: ${mode}`);
  apiPost('/api/change_mode', { mode });
}

function mission_start() {
  console.log('Mission start triggered');
  apiPost('/api/mission_start');
}

function abort_mission() {
  console.log('Abort mission triggered');
  apiPost('/api/abort_mission');
}

// ── Mode dropdown UI ────────────────────────────────────────────────────────

const MODES = ['MANUAL', 'FBWA', 'AUTO', 'GUIDED', 'RTL'];

function buildModeDropdown() {
  const wrapper = document.createElement('div');
  wrapper.className = 'mode-dropdown-wrapper';
  wrapper.style.position = 'relative';

  const dropdown = document.createElement('div');
  dropdown.className = 'mode-dropdown';
  dropdown.style.cssText = `
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    background: rgba(14, 28, 39, 0.98);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    overflow: hidden;
    margin-top: 4px;
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
      dropdown.style.display = 'none';
    });
    dropdown.appendChild(item);
  });

  wrapper.appendChild(dropdown);
  return { wrapper, dropdown };
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
  const { wrapper, dropdown } = buildModeDropdown();
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
  buttons[2].id = 'missionStartBtn';
  buttons[2].addEventListener('click', mission_start);

  // ABORT
  buttons[3].disabled = false;
  buttons[3].id = 'abortBtn';
  buttons[3].addEventListener('click', abort_mission);
}

window.addEventListener('DOMContentLoaded', setupActionButtons);