#!/usr/bin/env python3

import threading
import time
import os
import cv2
import numpy as np
import onnxruntime as ort
import paho.mqtt.client as mqtt
import face_recognition
from flask import Flask, Response, render_template_string

# ================= CONFIGURATION =================
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASS = ""

MQTT_TOPIC_IMAGE = "esp32/cam/image"
MQTT_TOPIC_WHOIS = "esp32/cam/whois"

MODEL_PATH = "yolov5n-face.onnx"
FACES_DIR = "known_faces"

# ================= GLOBAL VARIABLES =================
frame_lock = threading.Lock()
raw_jpeg_bytes = None       # The raw image coming from ESP32
processed_jpeg_bytes = None # The image AFTER drawing boxes (for web stream)

app = Flask(__name__)
mqtt_client = None

# Rate Limiter State
last_publish_time = 0
last_published_name = ""

# ================= MULTI-FACE MATCHER =================
class FaceMatcher:
    def __init__(self, faces_dir):
        self.known_encodings = []
        self.known_names = []
        print(f"Loading known faces from '{faces_dir}'...")
        if not os.path.exists(faces_dir):
            os.makedirs(faces_dir)
            return

        for filename in os.listdir(faces_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                path = os.path.join(faces_dir, filename)
                try:
                    img = face_recognition.load_image_file(path)
                    encodings = face_recognition.face_encodings(img)
                    if len(encodings) > 0:
                        name = os.path.splitext(filename)[0]
                        self.known_encodings.append(encodings[0])
                        self.known_names.append(name)
                        print(f"  Loaded: {name}")
                except Exception as e:
                    print(f"  Error loading {filename}: {e}")

    def identify(self, face_image_rgb):
        if len(self.known_encodings) == 0: return "Unknown"
        if face_image_rgb.size == 0: return "Unknown"

        try:
            face_image_rgb = np.ascontiguousarray(face_image_rgb)
            h, w, _ = face_image_rgb.shape
            face_encodings = face_recognition.face_encodings(face_image_rgb, [(0, w, h, 0)])
            
            if len(face_encodings) > 0:
                matches = face_recognition.face_distance(self.known_encodings, face_encodings[0])
                best_match_index = np.argmin(matches)
                if matches[best_match_index] < 0.55:
                    return self.known_names[best_match_index]
        except:
            pass
        return "Unknown"

# ================= YOLO DETECTOR =================
class YoloFaceDetector:
    def __init__(self, model_path, matcher):
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.input_h = self.session.get_inputs()[0].shape[2]
        self.input_w = self.session.get_inputs()[0].shape[3]
        self.matcher = matcher

    def preprocess(self, img):
        img_resized = cv2.resize(img, (self.input_w, self.input_h))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        img_data = img_rgb.astype(np.float32) / 255.0
        img_data = img_data.transpose(2, 0, 1)
        return np.expand_dims(img_data, axis=0)

    def detect_and_recognize(self, img):
        input_tensor = self.preprocess(img)
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        predictions = np.squeeze(outputs[0])

        orig_h, orig_w = img.shape[:2]
        scale_x = orig_w / self.input_w
        scale_y = orig_h / self.input_h

        boxes = []
        scores = []

        for row in predictions:
            score = row[4] * row[15]
            if score > 0.5:
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                boxes.append([
                    int((cx - w/2) * scale_x),
                    int((cy - h/2) * scale_y),
                    int(w * scale_x),
                    int(h * scale_y)
                ])
                scores.append(float(score))

        indices = cv2.dnn.NMSBoxes(boxes, scores, 0.5, 0.4)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        found_names = []

        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                x, y = max(0, x), max(0, y)
                w, h = min(w, orig_w - x), min(h, orig_h - y)

                face_crop = img_rgb[y:y+h, x:x+w]
                name = self.matcher.identify(face_crop)
                found_names.append(name)

                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
                cv2.putText(img, f"{name} ({scores[i]:.2f})", (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return img, found_names

# Initialize AI Components
matcher = FaceMatcher(FACES_DIR)
detector = YoloFaceDetector(MODEL_PATH, matcher)

# ================= BACKGROUND PROCESSING LOOP =================
def processing_loop():
    global raw_jpeg_bytes, processed_jpeg_bytes, last_publish_time, last_published_name
    
    print("Starting AI Processing Loop...")
    while True:
        # 1. Get latest raw image safely
        img_bytes = None
        with frame_lock:
            if raw_jpeg_bytes:
                img_bytes = raw_jpeg_bytes
        
        if img_bytes:
            try:
                # Decode
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    # Run AI
                    img, names = detector.detect_and_recognize(img)
                    
                    # Logic: Publish MQTT
                    current_time = time.time()
                    if names:
                        whois_msg = ", ".join(names)
                    else:
                        whois_msg = "No Face"

                    if whois_msg != last_published_name or (current_time - last_publish_time > 1.0):
                        if mqtt_client and mqtt_client.is_connected():
                            mqtt_client.publish(MQTT_TOPIC_WHOIS, whois_msg)
                            print(f"Published WHOIS: {whois_msg}")
                            last_published_name = whois_msg
                            last_publish_time = current_time

                    # Re-encode for Web Stream
                    ret, buffer = cv2.imencode('.jpg', img)
                    if ret:
                        with frame_lock:
                            processed_jpeg_bytes = buffer.tobytes()
            except Exception as e:
                print(f"Processing Error: {e}")

        # Limit CPU usage (approx 20 FPS max processing)
        time.sleep(0.05)

# ================= MQTT LOGIC =================
def on_message(client, userdata, msg):
    global raw_jpeg_bytes
    with frame_lock:
        raw_jpeg_bytes = msg.payload

def start_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
    mqtt_client.on_connect = lambda c, u, f, r: c.subscribe(MQTT_TOPIC_IMAGE)
    mqtt_client.on_message = on_message
    
    while True:
        try:
            print(f"Connecting to MQTT Broker {MQTT_BROKER}...")
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.loop_forever()
        except Exception as e:
            print(f"MQTT Error: {e}. Reconnecting in 5s...")
            time.sleep(5)

# ================= FLASK LOGIC =================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Feed</title>
    <style>
        body { margin: 0; padding: 0; background-color: #121212; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .container { background-color: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5); text-align: center; border: 1px solid #333; }
        h2 { margin-top: 0; margin-bottom: 15px; font-weight: 600; color: #4CAF50; letter-spacing: 1px; }
        .video-frame { border: 2px solid #333; border-radius: 8px; max-width: 100%; height: auto; display: block; }
        .status { margin-top: 10px; font-size: 0.9rem; color: #888; }
        .live-indicator { display: inline-block; width: 10px; height: 10px; background-color: red; border-radius: 50%; margin-right: 5px; animation: blink 1s infinite; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    </style>
</head>
<body>
<div class="container">
    <h2><span class="live-indicator"></span> LIVE FEED</h2>
    <img src="/video_feed" class="video-frame" alt="Video Stream">
    <div class="status">System Online &bull; Always-On Recognition Active</div>
</div>
</body>
</html>
"""

def generate_frames():
    global processed_jpeg_bytes
    while True:
        frame = None
        with frame_lock:
            if processed_jpeg_bytes:
                frame = processed_jpeg_bytes
        
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        time.sleep(0.05) 

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # 1. Thread for MQTT (Incoming Data)
    threading.Thread(target=start_mqtt, daemon=True).start()
    
    # 2. Thread for Processing (AI + Logic)
    threading.Thread(target=processing_loop, daemon=True).start()
    
    # 3. Main Thread for Flask (Serving Web Page)
    app.run(host='0.0.0.0', port=5000, debug=False)