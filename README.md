# NX2Touchpad

Turn your Nintendo Switch (with Atmosphere CFW) into a touchpad for your Linux PC over Wi-Fi.

To bypass strict Wayland/libinput touchpad rules, the Linux daemon emulates a standard mouse. All gestures work via the Python script.

## Current Features
- **1 Finger:** Move cursor
- **1 Finger Tap:** Left click
- **2 Fingers:** Vertical & Horizontal scrolling

---

## Linux PC Setup
1. Copy the `linux/` folder to your PC.
2. Install dependencies:
   ```bash
   cd linux
   chmod +x install.sh
   ./install.sh
   ```
3. **Firewall Requirement:** The daemon listens on UDP port `28275`. Make sure your firewall allows incoming traffic on this port.
   *(Example for iptables: `sudo iptables -I INPUT 1 -p udp --dport 28275 -j ACCEPT`)*
4. Run the daemon:
   ```bash
   sudo python3 nx2touchpad.py
   ```

---

## Nintendo Switch Setup
1. You need [devkitPro](https://devkitpro.org/) to compile the homebrew.
2. Build the `.nro`:
   ```bash
   cd switch
   make
   ```
3. Copy `NX2Touchpad.nro` to the `/switch/` folder on your SD card.
4. Launch it from the Homebrew Menu.
5. Use the D-Pad to enter your PC's IP address and press **A** to connect.
   *(Note: The Switch must be used in handheld mode, as the touchscreen is disabled when docked).*
