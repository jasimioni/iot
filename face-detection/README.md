# Face Detection / Recognition — README

Overview
--------
This repository contains tools to capture camera frames (ESP32), run fast face detection locally, recognize known people, and publish results over MQTT to drive a small web UI and a Node-RED dashboard.

Project structure (summary)
---------------------------
- web-ui.py  
    - Lightweight web UI + camera data stream. Uses yolov5-faces (fast detection) and the face_detection library for recognition. Consumes camera images from the MQTT stream and displays detections/recognitions.
- config.py  
    - Publishes configuration to the `cmd` MQTT topic (used by devices/services to receive configuration).
- netmon.py  
    - Monitors network traffic and publishes traffic/usage data to an MQTT topic.
- yolov5n-face.onnx  
    - Fast YOLOv5-based ONNX model tuned for face detection (used for quick on-device detection).
- known_faces/  
    - Folder with known face data used by the recognition routine (image samples)
- Image2MQTT  
    - ESP32-S3 firmware that reads the camera and publishes images to an MQTT topic. Optional local pre-filter: only publish when a face is detected using human_face_detect_msr01.
    - Note: human_face_detect_msr01 requires ESP core 3.0.7 (downgrade if needed).
- MQTTDisplayInfo  
    - ESP32-WROVER-DEV firmware to read recognition results from MQTT and show info on an LCD display.
- node-red/  
    - Node-RED flows/dashboard that aggregate camera, recognition, network and control topics.

Quick start
-----------
Prerequisites
- Python 3.8+ (for desktop components)
- pip packages typically needed: opencv-python, numpy, paho-mqtt, onnxruntime, flask (or fastapi), face_detection (install via pip if available) — check each script for exact imports.
- MQTT broker (e.g., Mosquitto)
- Node-RED (for dashboards)
- ESP32 toolchain / Arduino or PlatformIO for flashing ESP firmwares

Run (desktop components)
1. Configure your MQTT broker settings in the scripts (or set via the `config` publisher on the `cmd` topic).
2. Start the web UI:
     - python3 web-ui.py
     - Open the web UI in a browser (address printed by script).
3. Start network monitor:
     - python3 netmon.py
4. Import `node-red` flow into Node-RED to view the dashboard and link topics.

ESP32 components
- Image2MQTT (ESP32-S3)
    - Flash with Arduino/PlatformIO. If you use the human_face_detect_msr01 pre-filter, make sure the ESP core is 3.0.7 (downgrade your ESP32 board package if needed).
    - Flashes camera frames to the configured MQTT topic (optionally only when a face is detected).
- MQTTDisplayInfo (ESP32-WROVER-DEV)
    - Flash to ESP32-WROVER-DEV and wire the LCD. It subscribes to face recognition topics and displays recognized names/info.

MQTT topics (used)
- cmd — configuration commands (published by config)
- camera/... — image/frame stream from ESP (exact topic name found in Image2MQTT)
- face/recognized or face/results — recognition outputs (web UI / Node-RED consume these)
- netmon/traffic — network statistics published by netmon.py

Notes & tips
- Exact topic names and configuration keys are defined inside each script/firmware — inspect them before running.
- yolov5n-face.onnx is intended for fast inference; for higher accuracy replace with a larger model and adjust code.
- If using human_face_detect_msr01 on ESP32-S3: many newer ESP cores are incompatible — switch to core 3.0.7 in your board manager/toolchain.
- Keep known_faces updated with clean samples; re-generate embeddings if recognition quality drops.