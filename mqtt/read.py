#!/usr/bin/env python3
# /home/ubuntu/iot/mqtt/read
# Simple MQTT subscriber that prints messages from /AulaIoTPPGIa

import sys
import uuid
import os
import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_BROKER")
PORT = 1883
USERNAME = os.environ.get("MQTT_USERNAME")
PASSWORD = os.environ.get("MQTT_PASSWORD")
TOPIC = "/AulaIoTPPGIa"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
        client.subscribe(TOPIC)
        print(f"Subscribed to {TOPIC}")
    else:
        print(f"Connection failed with code {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8', errors='replace')
    except Exception:
        payload = str(msg.payload)
    print(f"[{msg.topic}] {payload}")

def main():
    client_id = f"mqtt-reader-{uuid.uuid4().hex[:8]}"
    client = mqtt.Client(client_id=client_id, clean_session=True)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
    except Exception as e:
        print(f"Could not connect to broker: {e}")
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Interrupted, disconnecting...")
        client.disconnect()

if __name__ == "__main__":
    main()