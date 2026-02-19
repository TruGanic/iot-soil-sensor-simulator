import qrcode
import json

# Read the sensor ID from your config
with open("config.json", "r") as f:
    config = json.load(f)

sensor_id = config["sensor_id"]

# Create the QR Code
qr = qrcode.make(sensor_id)
qr.show() # This pops up an image of the QR code on your screen!

print(f"✅ Generated QR Code for Sensor: {sensor_id}")