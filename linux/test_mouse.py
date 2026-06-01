#!/usr/bin/env python3
import time
from evdev import UInput, ecodes as e

cap = { 
    e.EV_REL: [e.REL_X, e.REL_Y], 
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT] 
}

try:
    ui = UInput(cap, name="TestMouse", vendor=0x1234, product=0x5678, version=1)
except Exception as ex:
    print(f"Error: {ex}")
    exit(1)

print("Moving mouse to the right...")
time.sleep(1) # Give Wayland a second to register the device

for i in range(50):
    ui.write(e.EV_REL, e.REL_X, 10)
    ui.syn()
    time.sleep(0.02)

print("Done.")
ui.close()
