#!/usr/bin/env python3

import sys
import time
import os

import paho.mqtt.client as mqtt

def main():
    if len(sys.argv) < 2:
        print("Usage: write.py <message>")
        sys.exit(1)

    message = sys.argv[1]
    broker = os.environ.get("MQTT_BROKER")
    port = 1883
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    topic = "/semaforo/commands"

    client = mqtt.Client()
    client.username_pw_set(username, password)

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        print("Failed to connect to broker:", e)
        sys.exit(2)

    client.loop_start()
    try:
        info = client.publish(topic, payload=message, qos=1)
        info.wait_for_publish()
    except Exception as e:
        print("Publish failed:", e)
        sys.exit(3)
    finally:
        time.sleep(0.1)
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()