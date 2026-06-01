#!/bin/bash
set -e

echo "Installing NX2Touchpad Linux Daemon dependencies..."
sudo apt-get update || true
sudo apt-get install -y python3 python3-pip || true

echo "Installing python-evdev..."
sudo pip3 install evdev --break-system-packages || sudo pip3 install evdev

echo "Creating udev rule for uinput..."
echo 'KERNEL=="uinput", MODE="0660", GROUP="input"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Setup complete! You may need to add your user to the input group:"
echo "sudo usermod -aG input $USER"
echo "Then log out and log back in."
