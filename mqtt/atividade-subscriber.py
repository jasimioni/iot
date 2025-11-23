#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import os

broker_address = os.environ.get("MQTT_BROKER")
broker_username = os.environ.get("MQTT_USERNAME")
broker_password = os.environ.get("MQTT_PASSWORD")
port = 1883
topic = "\\Aula02\\JoaoSimioni\\Hora"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado com sucesso!")
        client.subscribe(topic)
        print(f"Inscrito no tópico: {topic}")
    else:
        print(f"Falha na conexão. Código: {rc}")

def on_message(client, userdata, msg):
    mensagem = msg.payload.decode()
    print(f"Mensagem Recebida: {mensagem}")

client = mqtt.Client()
client.username_pw_set(broker_username, broker_password)

client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"Conectando ao broker {broker_address}...")
    client.connect(broker_address, port)
    
    client.loop_forever()

except KeyboardInterrupt:
    print("\nEncerrando assinante...")
    client.disconnect()
except Exception as e:
    print(f"Erro: {e}")
