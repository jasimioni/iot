#!/usr/bin/env python3

# 

import sys
import time
import os

import paho.mqtt.client as mqtt

def main():
    broker = os.environ.get("MQTT_BROKER")
    port = 1883
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    
    sequence = [
        ( 'red', 7 ),
        ( 'green', 5 ),
        ( 'yellow', 2 )
    ]

    client = mqtt.Client()
    client.username_pw_set(username, password)
    topic_base = "/semaforo/"

    try:
        client.connect(broker, port, keepalive=60)
    except Exception as e:
        print("Failed to connect to broker:", e)
        sys.exit(2)

    client.loop_start()
    
    while (True):
        # ensure we're connected, try to reconnect with exponential backoff if not
        if not client.is_connected():
            print("MQTT client disconnected, attempting to reconnect...")
            backoff = 1
            while not client.is_connected():
                try:
                    client.reconnect()
                    print("Reconnected to broker")
                    break
                except Exception as e:
                    print(f"Reconnect failed: {e}; retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 30)
        
        next = sequence.pop(0)
        sequence.append(next)
        light, delay = next
        
        try:
            red = 'desliga'
            yellow = 'desliga'
            green = 'desliga'
            if light == 'red':
                red = 'liga'
            elif light == 'yellow':
                yellow = 'liga'
            elif light == 'green':
                green = 'liga'
            
            info = client.publish(topic_base + 'red', payload=red, qos=1)
            info.wait_for_publish()
            print("Published red light command")
            info = client.publish(topic_base + 'yellow', payload=yellow, qos=1)
            info.wait_for_publish()
            print("Published yellow light command")
            info = client.publish(topic_base + 'green', payload=green, qos=1)
            info.wait_for_publish()
            print("Published green light command")
        
            print(f"Set light to {light} for {delay} seconds")
        except Exception as e:
            print("Publish failed:", e)

        time.sleep(delay)


if __name__ == "__main__":
    main()