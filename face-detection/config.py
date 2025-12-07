#!/usr/bin/env python3

import time
import random
import sys
from paho.mqtt import client as mqtt_client

MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASS = ""
MQTT_TOPIC_CMD = "esp32/cam/cmd"


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_PORT)
    return client

if __name__ == '__main__':
    client = connect_mqtt()
    client.loop_start()
    msg = sys.argv[1]
    result = client.publish(MQTT_TOPIC_CMD, msg)
    print("Published `%s` to `%s`" % (msg, MQTT_TOPIC_CMD))
    client.loop_stop()
