#!/bin/bash

TARGET_IP="10.0.0.191"   # Thermostat IP
KASA_IP="10.0.0.26"      # Smart Plug IP
RETRY_LIMIT=30           # Consecutive failure limit
PING_INTERVAL=2          # Seconds between pings
LOG_FILE="./reset.log"   # Log file path
CHECK_DELAY=600          # Delay after reset in seconds

export PATH=$PATH:/home/jason/.local/bin

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

# Function to reset the smart plug device
reset_device() {
    log_message "Resetting device at $KASA_IP"
    kasa --host $KASA_IP off
    sleep 30
    kasa --host $KASA_IP on
    log_message "Device reset complete. Waiting $CHECK_DELAY seconds."
    sleep $CHECK_DELAY
}

# Main loop
failure_count=0
while true; do
    if ping -c 1 -W 1 $TARGET_IP &> /dev/null; then
        log_message "Ping to $TARGET_IP successful."
        failure_count=0  # Reset failure count on successful ping
    else
        log_message "Ping to $TARGET_IP failed."
        ((failure_count++))
    fi

    # Reset device if failures reach the limit
    if [ $failure_count -ge $RETRY_LIMIT ]; then
        log_message "Consecutive failures reached $RETRY_LIMIT. Initiating reset."
        reset_device
        failure_count=0  # Reset failure count after a reset
    fi

    sleep $PING_INTERVAL  # Wait before the next ping
done
