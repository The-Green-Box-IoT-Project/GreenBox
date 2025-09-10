# actuator.py
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected to broker with result code:", rc)
    # Iscriviti a tutti i topic sotto "GreenBox/"
    client.subscribe("GreenBox/#")
    print("Subscribed to GreenBox/#")
    
def on_message(client, userdata, msg):
    print(f"Received message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print("Payload:", payload)
        # Qui inserisci la logica per attivare/disattivare il dispositivo fisico
    except Exception as e:
        print("Error processing message:", e)

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
