#!/usr/bin/env python3

import time
import threading
import paho.mqtt.client as mqtt
from scapy.all import sniff, TCP, IP
from collections import deque
import json

# ================= CONFIGURATION =================
MONITOR_INTERFACE = "eth0"  # Change to your interface (e.g., 'wlan0', 'lo')
FILTER_PORT = 1883

# MQTT Settings (Where to publish the stats)
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASS = ""
TOPIC_STATS = "monitor/traffic/1883"

# ================= GLOBAL STATE =================
# Stores tuples of (timestamp, byte_count)
packet_history = deque()
history_lock = threading.Lock()

# ================= MQTT SETUP =================
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)

def connect_mqtt():
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("Connected to MQTT broker for publishing stats.")
    except Exception as e:
        print(f"MQTT Connection Error: {e}")

# ================= PACKET SNIFFER =================
def process_packet(packet):
    """ Callback for every packet captured on port 1883 """
    # Get packet length (Wire length is best, otherwise IP len)
    pkt_len = len(packet)
    
    current_time = time.time()
    
    with history_lock:
        packet_history.append((current_time, pkt_len))

def start_sniffer():
    print(f"Starting capture on {MONITOR_INTERFACE} port {FILTER_PORT}...")
    # Filter for TCP traffic on port 1883
    bpf_filter = f"tcp and port {FILTER_PORT}"
    
    # store=0 prevents storing packets in RAM (memory leak prevention)
    sniff(iface=MONITOR_INTERFACE, filter=bpf_filter, prn=process_packet, store=0)

# ================= CALCULATOR LOOP =================
def calculate_rate(window_seconds, current_time):
    """ Calculates BPS over the last X seconds """
    total_bytes = 0
    cutoff_time = current_time - window_seconds
    
    # Iterate through history
    # Note: In a high-traffic production env, this iteration might be slow.
    # For MQTT traffic, a deque is usually sufficient.
    for ts, size in reversed(packet_history):
        if ts < cutoff_time:
            break
        total_bytes += size
        
    # Bits per second = (Bytes * 8) / Time Window
    bps = (total_bytes * 8) / window_seconds
    return int(bps)

def stats_loop():
    while True:
        time.sleep(1) # Calculate every second
        current_time = time.time()
        
        # 1. Clean up old history (older than 60s)
        with history_lock:
            while len(packet_history) > 0 and packet_history[0][0] < (current_time - 65):
                packet_history.popleft()
            
            # Copy to avoid locking during calculation
            # (Optional optimization, but safe for simple scripts to just calculate inside lock)
            
            # 2. Calculate Rates
            bps_5s = calculate_rate(5, current_time)
            bps_15s = calculate_rate(15, current_time)
            bps_60s = calculate_rate(60, current_time)

        # 3. Publish
        data = {
                'bps_5s' : bps_5s,
                'bps_15s' : bps_15s,
                'bps_60s' : bps_60s
        }
        payload = json.dumps(data)
        print(f"[Stats] {payload}")
        
        if client.is_connected():
            client.publish(TOPIC_STATS, payload)

# ================= MAIN =================
if __name__ == "__main__":
    connect_mqtt()

    # Start Stats Thread
    t_stats = threading.Thread(target=stats_loop)
    t_stats.daemon = True
    t_stats.start()

    # Start Sniffer (Blocks main thread)
    # sudo is usually required for this part
    try:
        start_sniffer()
    except PermissionError:
        print("Error: Packet sniffing requires root privileges. Try running with 'sudo'.")
    except Exception as e:
        print(f"Sniffer Error: {e}")
