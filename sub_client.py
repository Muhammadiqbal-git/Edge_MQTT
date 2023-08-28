import sys
from paho.mqtt import client as mqtt_client

broker_address = '192.168.100.2'
port = 1883
topic = 'edge/cam/1'

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

def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print("Recieved data from {} topic".format(msg.topic))
        print("Data : {}".format(msg.payload.decode()))

    client.subscribe(topic)
    client.on_message = on_message

def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()

if __name__ == '__main__':
    run()
