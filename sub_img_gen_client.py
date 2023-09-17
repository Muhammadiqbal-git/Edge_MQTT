from paho.mqtt import client as mqtt_client
from PIL import Image
import io
import os
import random
import time

broker_address = '192.168.100.2'
port = 1883
topic = [('edge/cam/1', 0), ('edge/cam/2', 0)]

client_id = 'img_gen_1'


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

def get_dir():
    target_dir = os.path.join('.', 'img')
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    return target_dir

def subscribe_mqtt(client: mqtt_client):
    def on_message(client, userdata, msg):
        print("Recieved data from {} topic".format(msg.topic))
        if (msg.topic == 'edge/cam/1'):
            print("Recieved from first topic")
        print("Data : {}".format(msg.payload))
        print("Lenght : {}".format(len(msg.payload)))
        img_data = io.BytesIO(msg.payload)
        t_dir = get_dir()
        time_now = time.strftime("%Y-%m-%d")
        img_name = "{}_{}.jpeg".format(random.randint(1111, 9999), time_now)
        img_path = os.path.join(t_dir, img_name)
        im = Image.open(img_data)
        im.save(img_path)
        if os.path.exists(img_path):
            print(img_name, "saved succesfully")
    client.subscribe(topic)
    client.on_message = on_message

def run():
    print("Subscriber img data generator running....")
    get_dir()
    client = connect_mqtt()
    subscribe_mqtt(client)
    client.loop_forever()

if __name__ == '__main__':
    run()
