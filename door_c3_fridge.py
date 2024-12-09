import network
import time
from machine import Pin, unique_id
import ubinascii
from umqtt.simple import MQTTClient

# Wi-Fi credentials
SSID = "AAL_HOUSE"
PASSWORD = "Sm@rtTH0usE21"

# MQTT Broker details
MQTT_BROKER = "10.10.30.200"
MQTT_PORT = 1883
MQTT_TOPIC = "home/door_fridge"
MQTT_CLIENT_ID = ubinascii.hexlify(unique_id()).decode()

# GPIO Pin for reed switch
REED_SWITCH_PIN = 5

# Initialize reed switch with internal pull-up resistor
reed_switch = Pin(REED_SWITCH_PIN, Pin.IN, Pin.PULL_UP)

# Connect to Wi-Fi
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Already connected to Wi-Fi")
        return wlan

    print(f"Connecting to Wi-Fi: {SSID}...")
    wlan.connect(SSID, PASSWORD)

    # Wait for connection
    for _ in range(20):  # 20 seconds timeout
        if wlan.isconnected():
            print("Wi-Fi connected")
            print("Network config:", wlan.ifconfig())
            return wlan
        time.sleep(1)

    # Fail if unable to connect
    raise RuntimeError("Failed to connect to Wi-Fi")

# Publish MQTT message
def send_mqtt_message(client, message):
    try:
        client.publish(MQTT_TOPIC, message)
        print(f"MQTT message sent: {message}")
    except OSError as e:
        print(f"Failed to send MQTT message: {e}")
        try:
            print("Attempting to reconnect to MQTT broker...")
            client.connect()  # Reconnect to the broker
            client.publish(MQTT_TOPIC, message)  # Retry sending the message
            print(f"MQTT message sent after reconnect: {message}")
        except Exception as reconnection_error:
            print(f"Reconnection failed: {reconnection_error}")

# Monitor door and send status
def monitor_door(client):
    prev_status = None
    last_change = 0
    debounce_delay = 200  # 200ms debounce delay
    door_open_time = None
    alarm_sent = False

    while True:
        # Check reed switch state
        current_time = time.ticks_ms()
        status = reed_switch.value() == 1  # 1 = Open, 0 = Closed

        if status != prev_status and time.ticks_diff(current_time, last_change) > debounce_delay:
            prev_status = status
            last_change = current_time
            door_fridge = "Open" if status else "Closed"
            print(f"Door is {door_fridge}")
            send_mqtt_message(client, door_fridge)

            if status:  # Door just opened
                door_open_time = current_time
                alarm_sent = False  # Reset alarm flag when door opens
            else:  # Door just closed
                door_open_time = None
                alarm_sent = False  # Reset alarm flag when door closes

        # Check if the door has been open for more than 10 seconds
        if status and door_open_time is not None and not alarm_sent:
            elapsed_time = time.ticks_diff(current_time, door_open_time)
            if elapsed_time >= 10000:  # 10 seconds in milliseconds
                # Send alarm
                alarm_message = "ξεχάσατε την πόρτα ανοιχτή"
                send_mqtt_message(client, alarm_message)
                print(alarm_message)
                alarm_sent = True  # Ensure alarm is sent only once per event

        time.sleep(0.1)

# Main execution
try:
    # Connect to Wi-Fi
    wlan = connect_to_wifi()

    # Connect to MQTT broker
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    mqtt_client.connect()
    print(f"Connected to MQTT broker at {MQTT_BROKER}")

    # Monitor door and send status
    monitor_door(mqtt_client)
except Exception as e:
    print(f"Error: {e}")
