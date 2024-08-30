#!/bin/bash
while true; do
    if dmesg | grep -q "Out of memory"; then
        echo "OOM detected, rebooting..."
        sudo reboot
    fi
    sleep 60
done

