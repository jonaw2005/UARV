<div align="center">

# 🛩️ UARV — Unmanned Aerial Reconnaisance Vehicle

**A full-stack MAVLink ground control system for ArduPilot/PX4-based drones**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)
![Socket.IO](https://img.shields.io/badge/Socket.IO-4.7-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![MAVLink](https://img.shields.io/badge/MAVLink-2.0-FF6B35?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij48cGF0aCBkPSJNMzIgMkwyIDU0aDYweiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjQiLz48L3N2Zz4=&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-C51A4A?style=for-the-badge&logo=raspberry-pi&logoColor=white)
![NGINX](https://img.shields.io/badge/NGINX-1.24-009639?style=for-the-badge&logo=nginx&logoColor=white)

---

[✨ Features](#-features) • [🏗️ Architecture](#️-architecture) • [🚀 Getting Started](#-getting-started) • [📡 API Reference](#-api-reference) • [🖥️ Web Interface](#️-web-interface) • [🛠️ Configuration](#️-configuration) • [📁 Project Structure](#-project-structure)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎮 Full Drone Control
- **Arm / Disarm** with safety confirmation
- **Flight mode switching** (MANUAL, FBWA, AUTO, GUIDED, RTL, LOITER, STABILIZE, LAND)
- **Takeoff** with automatic GUIDED mode transition
- **Velocity control** (local NED frame)
- **GPS waypoint navigation** (`goto` command)
- **Mission upload & download** with full MAVLink protocol support
- **Emergency abort** (disarm + switch to MANUAL)

</td>
<td width="50%">

### 📊 Real-Time Telemetry
- **GPS position** (latitude, longitude, altitude)
- **Attitude** (roll, pitch, yaw)
- **Velocity** (ground speed, airspeed, climb rate)
- **Battery status** (voltage, current, remaining %)
- **GPS quality** (fix type, satellite count)
- **System health** (connected status, heartbeat)
- **Live video stream** via Socket.IO at ~30 FPS

</td>
</tr>
<tr>
<td width="50%">

### 🗺️ Interactive Map
- **Leaflet-based** with OpenStreetMap tiles
- **Real-time aircraft position** with heading indicator
- **Rotating triangle marker** showing drone orientation
- **Auto-centering** on GPS coordinates
- **Telemetry data** in a draggable floating window

</td>
<td width="50%">

### 📋 Mission Planner
- **Visual waypoint placement** by clicking on the map
- **Action insertion** (takeoff, loiter, RTL, land, delay, speed, yaw)
- **Drag-and-drop reordering** of mission items
- **Mission upload** to Pixhawk via MAVLink
- **Mission download** from Pixhawk
- **Coordinate input** for precise waypoint placement

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (onboard)                   │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │  controll_api.py │◄──►│        mav_bridge.py         │   │
│  │  (Flask + Socket)│    │   (pymavlink MAVLink bridge) │   │
│  └──────┬───────────┘    └──────────┬───────────────────┘   │
│         │                           │                       │
│         │ HTTP/WS                   │ UART (921600 baud)    │
│         ▼                           ▼                       │
│  ┌──────────────┐          ┌──────────────┐                 │
│  │  Web Browser │          │   Pixhawk    │                 │
│  │  (Admin UI)  │          │  (ArduPilot) │                 │
│  └──────────────┘          └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **`controll_api.py`** | Flask + Flask-SocketIO | REST API server & WebSocket video streaming |
| **`mav_bridge.py`** | pymavlink | MAVLink protocol bridge to Pixhawk over UART |
| **`admin_panel/`** | HTML/CSS/JS + Leaflet | Web-based ground control interface |
| **`config.js`** | JavaScript | Dynamic API URL resolution via `window.location.origin` |

---

## 🚀 Getting Started

### Prerequisites

- **Hardware:** Raspberry Pi (any model with UART), Pixhawk (or any ArduPilot/PX4 autopilot)
- **Connection:** Pixhawk connected to Raspberry Pi UART (`/dev/ttyAMA0`)
- **Software:** Python 3.10+, pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/jonaw2005/UARV.git
cd UARV

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

### Running

```bash
# Start the API server (default: port 8000)
python controll_api.py
```

The web interface will be available at: **`http://<raspberry-pi-ip>:8000`**

> **Note:** The web interface automatically detects the server's IP address using `window.location.origin` — no hardcoded IPs needed!

---

## 📡 API Reference

### Status & Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | API health check |
| `/api/get_health` | GET | System health status |
| `/api/get_telemetry` | GET | Full telemetry data |
| `/api/get_location` | GET | GPS location only |

### Vehicle Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/arm` | GET | Arm the vehicle |
| `/api/disarm` | GET | Disarm the vehicle |
| `/api/arm_disarm` | GET | Toggle arm/disarm |
| `/api/is_armed` | GET | Check armed status |
| `/api/takeoff` | GET | Takeoff (switches to GUIDED) |
| `/api/change_flightmode` | POST | Change flight mode |
| `/api/get_flightmode` | GET | Get current flight mode |
| `/api/set_velocity` | POST | Set velocity (vx, vy, vz) |
| `/api/goto` | POST | Go to GPS coordinate |

### Mission Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mission_upload` | POST | Upload mission to Pixhawk |
| `/api/mission_download` | GET | Download mission from Pixhawk |
| `/api/mission_start` | GET | Start mission (switch to AUTO) |
| `/api/abort_mission` | GET | Abort mission (disarm + MANUAL) |

### Parameters & GPS

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/get_param` | POST | Read a single parameter |
| `/api/get_param_test` | GET | Test: read STAT_RUNTIME |
| `/api/get_all_params` | GET | Read all parameters |
| `/api/get_gps` | GET | GPS position (GLOBAL_POSITION_INT) |
| `/api/get_gps_raw` | GET | GPS position (GPS_RAW_INT) |
| `/api/gps_status` | GET | GPS fix type & satellites |
| `/api/battery_level` | GET | Battery voltage, current, remaining |

### Video Streaming

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video` | GET | MJPEG video stream |
| Socket.IO `video_frame` | WS | Base64-encoded JPEG frames |

---

## 🖥️ Web Interface

### Dashboard (`index.html`)

The main dashboard provides three panels:

<table>
<tr>
<th>Panel</th>
<th>Features</th>
</tr>
<tr>
<td><strong>📷 Live Camera</strong></td>
<td>Real-time video stream from the onboard camera via Socket.IO. Displays connection status and stream URL.</td>
</tr>
<tr>
<td><strong>🗺️ Interactive Map</strong></td>
<td>
• Leaflet map with OpenStreetMap tiles<br>
• Aircraft position with heading-indicating triangle marker<br>
• GPS coordinate display (lat/lon)<br>
• Telemetry floating window (attitude, velocity, battery, GPS)<br>
• Mission Order floating window (downloaded mission display)
</td>
</tr>
<tr>
<td><strong>🎮 Controls</strong></td>
<td>
• Arm/Disarm toggle with automatic status polling (every 3s)<br>
• Flight mode dropdown (MANUAL, FBWA, AUTO, GUIDED, RTL, LOITER, STABILIZE, LAND)<br>
• Takeoff button<br>
• Abort button<br>
• Mission Planner link<br>
• Mission Order download button
</td>
</tr>
</table>

### Mission Planner (`mission_planner.html`)

A full-featured mission planning interface:

- **Click-to-place waypoints** on the map
- **Action insertion** with parameter configuration
- **Drag-and-drop reordering** of mission items
- **Coordinate form** for precise waypoint entry
- **Mission upload** to Pixhawk (converts to MAVLink format)
- **Mission download** from Pixhawk
- **Numbered markers** and route polyline visualization

---

## 🛠️ Configuration

### Pixhawk Connection

The connection is configured in `controll_api.py`:

```python
bridge = MAVBridge("/dev/ttyAMA0", baud=921600)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `connection_string` | `/dev/ttyAMA0` | UART device path |
| `baud` | `921600` | Baud rate (must match Pixhawk) |
| `source_system` | `255` | MAVLink system ID |

### Web Interface

All API URLs are dynamically resolved using `window.location.origin` (defined in `admin_panel/config.js`). No configuration needed — just access the web interface from any device on the same network.

---

## 📁 Project Structure

```
UARV/
├── controll_api.py          # Flask REST API + Socket.IO server
├── mav_bridge.py            # MAVLink protocol bridge
├── mav_bridge_backup.py     # Backup of original bridge
├── mav_test.py              # MAVLink test script
├── requirements.txt         # Python dependencies
├── servo_test.py            # Servo test script
├── test_mission_download.py # Mission download test
├── test_mission_upload.py   # Mission upload test
├── update_uarv.sh           # Update script
├── README.md                # This file
│
└── admin_panel/             # Web frontend
    ├── config.js            # Shared configuration (API_BASE)
    ├── index.html           # Main dashboard
    ├── mission_planner.html # Mission planner interface
    ├── stylesheet.css       # Main stylesheet
    ├── mission_planner.css  # Mission planner styles
    ├── buttons.js           # Control buttons & arm status polling
    ├── camera.js            # Socket.IO video stream client
    ├── map.js               # Leaflet map, telemetry, mission display
    ├── mission_planner.js   # Mission planning logic
    ├── logo.png             # UARV logo
    └── ...
```

---

## 🔧 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `flask` | ≥2.0 | Web framework |
| `flask-socketio` | ≥5.0 | WebSocket support for video streaming |
| `pymavlink` | ≥2.4 | MAVLink protocol implementation |
| `opencv-python` | ≥4.5 | Camera capture & JPEG encoding |
| `eventlet` | — | (Removed — conflicts with pymavlink) |

---

## ⚠️ Troubleshooting

### "Pixhawk not responding"
- Check UART connection (`/dev/ttyAMA0`)
- Verify baud rate matches Pixhawk configuration (921600)
- Ensure Pixhawk is powered and running ArduPilot

### "Arm command fails"
- Check pre-arm status in telemetry
- Ensure the vehicle is in GUIDED or STABILIZE mode
- Verify GPS has a 3D fix

### "Video stream not loading"
- Check camera connection (`/dev/video0`)
- Verify the API server is running on port 8000
- Check browser console for Socket.IO connection errors

---

<div align="center">

**Built with ❤️ for the UARV project**

[![GitHub](https://img.shields.io/badge/GitHub-jonaw2005%2FUARV-181717?style=for-the-badge&logo=github)](https://github.com/jonaw2005/UARV)

</div>