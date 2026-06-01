#!/usr/bin/env python3
import socket
import struct
import time

PORT = 28275
IP = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_touch(count, touches, timestamp):
    packet = struct.pack('<4sBBBBQ', b'NX2T', 1, 0, count, 0, timestamp)
    for t in touches:
        packet += struct.pack('<IHHHH', t['id'], t['x'], t['y'], t['dx'], t['dy'])
    sock.sendto(packet, (IP, PORT))

try:
    print(f"Sending fake touch data to {IP}:{PORT}...")
    ts = 0
    print("Simulating single finger movement...")
    for x in range(100, 1000, 10):
        send_touch(1, [{'id': 1, 'x': x, 'y': 360, 'dx': 10, 'dy': 10}], ts)
        ts += 1
        time.sleep(0.01)
        
    # Release
    send_touch(0, [], ts)
    print("Done")
except KeyboardInterrupt:
    pass
