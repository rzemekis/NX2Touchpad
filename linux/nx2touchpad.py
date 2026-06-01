#!/usr/bin/env python3
import struct
import socket
import time
import select
import sys
from evdev import UInput, ecodes as e

PORT = 28275

# Emulate a standard Relative Mouse (always accepted by Wayland/X11)
cap = {
    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL],
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE]
}

def main():
    print("Starting NX2Touchpad Linux Daemon (Relative Mode)...")
    
    try:
        ui = UInput(cap, name="NX2Touchpad", vendor=0x1234, product=0x5678, version=1)
    except Exception as ex:
        print(f"Failed to create uinput device: {ex}")
        sys.exit(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT))
    sock.setblocking(False)
    
    print(f"Listening on UDP port {PORT}...")
    
    last_packet_time = time.time()
    
    # Touch state for gestures
    prev_touches = {} # id -> (x, y)
    touch_start_times = {} # id -> time
    touch_start_pos = {} # id -> (x, y)
    
    SENSITIVITY = 1.5
    SCROLL_SENSITIVITY = 0.05
    TAP_TIME = 0.25 # seconds
    TAP_DIST = 20 # pixels
    
    scroll_accum_y = 0.0
    scroll_accum_x = 0.0

    try:
        while True:
            ready = select.select([sock], [], [], 1.0)
            if not ready[0]:
                if time.time() - last_packet_time > 2.0 and prev_touches:
                    prev_touches.clear()
                    touch_start_times.clear()
                    touch_start_pos.clear()
                continue
                
            data, addr = sock.recvfrom(1024)
            last_packet_time = time.time()
            
            if len(data) < 16:
                continue
                
            magic = data[0:4]
            if magic != b'NX2T':
                continue
                
            pkt_type = data[5]
            touch_count = data[6]
            
            if pkt_type == 2: # Disconnect
                prev_touches.clear()
                touch_start_times.clear()
                touch_start_pos.clear()
                continue
                
            touches = []
            offset = 16
            for _ in range(touch_count):
                if offset + 12 > len(data): break
                finger_id, x, y, dx, dy = struct.unpack('<IHHHH', data[offset:offset+12])
                touches.append({'id': finger_id, 'x': x, 'y': y})
                offset += 12
                
            # DEBUG PRINT:
            if not hasattr(main, 'last_touch_count'): main.last_touch_count = -1
            if touch_count != main.last_touch_count:
                print(f"DEBUG: Received {touch_count} touches from {addr}")
                main.last_touch_count = touch_count
                
            current_ids = {t['id'] for t in touches}
            
            # Detect released touches (for tap-to-click)
            for tid in list(touch_start_times.keys()):
                if tid not in current_ids:
                    # Released! Check if it was a tap
                    duration = time.time() - touch_start_times[tid]
                    start_x, start_y = touch_start_pos[tid]
                    last_x, last_y = prev_touches.get(tid, (start_x, start_y))
                    dist = ((last_x - start_x)**2 + (last_y - start_y)**2)**0.5
                    
                    if duration < TAP_TIME and dist < TAP_DIST:
                        # TAP detected!
                        if touch_count == 0 and len(prev_touches) == 1:
                            # Left click
                            ui.write(e.EV_KEY, e.BTN_LEFT, 1)
                            ui.syn()
                            time.sleep(0.01)
                            ui.write(e.EV_KEY, e.BTN_LEFT, 0)
                            ui.syn()
                    
                    del touch_start_times[tid]
                    del touch_start_pos[tid]
                    if tid in prev_touches:
                        del prev_touches[tid]
            
            # Process current touches
            if touch_count == 1:
                t = touches[0]
                tid = t['id']
                if tid in prev_touches:
                    dx = t['x'] - prev_touches[tid][0]
                    dy = t['y'] - prev_touches[tid][1]
                    
                    move_x = int(dx * SENSITIVITY)
                    move_y = int(dy * SENSITIVITY)
                    
                    if move_x != 0 or move_y != 0:
                        if move_x != 0: ui.write(e.EV_REL, e.REL_X, move_x)
                        if move_y != 0: ui.write(e.EV_REL, e.REL_Y, move_y)
                        ui.syn()
                        
                else:
                    # New touch
                    touch_start_times[tid] = time.time()
                    touch_start_pos[tid] = (t['x'], t['y'])
                    
                prev_touches[tid] = (t['x'], t['y'])
                
            elif touch_count == 2:
                # Two finger scroll
                t1, t2 = touches[0], touches[1]
                id1, id2 = t1['id'], t2['id']
                
                if id1 in prev_touches and id2 in prev_touches:
                    dy1 = t1['y'] - prev_touches[id1][1]
                    dy2 = t2['y'] - prev_touches[id2][1]
                    dx1 = t1['x'] - prev_touches[id1][0]
                    dx2 = t2['x'] - prev_touches[id2][0]
                    
                    # Average movement
                    avg_dy = (dy1 + dy2) / 2.0
                    avg_dx = (dx1 + dx2) / 2.0
                    
                    scroll_accum_y += avg_dy * SCROLL_SENSITIVITY
                    scroll_accum_x += avg_dx * SCROLL_SENSITIVITY
                    
                    scroll_y = 0
                    scroll_x = 0
                    
                    if abs(scroll_accum_y) >= 1.0:
                        scroll_y = int(-scroll_accum_y) # Invert for natural scroll
                        scroll_accum_y -= -scroll_y
                        
                    if abs(scroll_accum_x) >= 1.0:
                        scroll_x = int(scroll_accum_x)
                        scroll_accum_x -= scroll_x
                        
                    if scroll_y != 0: ui.write(e.EV_REL, e.REL_WHEEL, scroll_y)
                    if scroll_x != 0: ui.write(e.EV_REL, e.REL_HWHEEL, scroll_x)
                    if scroll_y != 0 or scroll_x != 0: ui.syn()
                    
                else:
                    if id1 not in touch_start_times:
                        touch_start_times[id1] = time.time()
                        touch_start_pos[id1] = (t1['x'], t1['y'])
                    if id2 not in touch_start_times:
                        touch_start_times[id2] = time.time()
                        touch_start_pos[id2] = (t2['x'], t2['y'])
                        
                prev_touches[id1] = (t1['x'], t1['y'])
                prev_touches[id2] = (t2['x'], t2['y'])
            else:
                # 3+ fingers or 0 fingers, just update positions to avoid jumps
                for t in touches:
                    prev_touches[t['id']] = (t['x'], t['y'])

    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        ui.close()
        sock.close()

if __name__ == '__main__':
    main()
