import sys
from paho.mqtt import client as mqtt_client
from PIL import Image
import io

broker_address = '192.168.100.2'
port = 1883
topic = [('edge/cam/1', 0), ('edge/cam/2', 0)]

client_id = 'edge_1'


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print('Connected to MQTT Broker!')
        else:
            print('Failed to connect with return code {}'.format(rc))
    client = mqtt_client.Client(client_id=client_id)
    client.on_connect = on_connect
    client.connect(broker_address, port)
    return client

def subscribe_mqtt(client: mqtt_client):
    def on_message(client, userdata, msg):
        print("Recieved data from {} topic".format(msg.topic))
        if (msg.topic == 'edge/cam/1'):
            print("Recieved from first topic")
        print("Data : {}".format(msg.payload))
        print("Lenght : {}".format(len(msg.payload)))
        tes = io.BytesIO(msg.payload)
        im = Image.open(tes)
        print(im)
        im.show()


    client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt()
    subscribe_mqtt(client)
    client.loop_forever()

if __name__ == '__main__':
    run()
