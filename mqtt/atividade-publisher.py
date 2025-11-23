#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
from datetime import datetime
import os

broker_address = os.environ.get("MQTT_BROKER")
broker_username = os.environ.get("MQTT_USERNAME")
broker_password = os.environ.get("MQTT_PASSWORD")
port = 1883
topic = "\Aula02\JoaoSimioni\Hora" 

client = mqtt.Client()

try:
    print(f"Conectando ao broker {broker_address}...")
    client.username_pw_set(broker_username, broker_password)
    client.connect(broker_address, port)
    
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        client.publish(topic, now)
        print(f"Enviado: {now} para o tópico {topic}")
        time.sleep(1)

except KeyboardInterrupt:
    print("\nEncerrando publicador...")
    client.disconnect()
except Exception as e:
    print(f"Erro: {e}")
