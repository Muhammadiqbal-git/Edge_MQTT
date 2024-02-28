import time
import random
import os
import io
from paho.mqtt import client as mqtt_client
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

broker_address = 'serveo.net'
port = 1883
topic = [('edge/cam/1/time', 0), ('edge/cam/1/inprogress', 0), ('edge/cam/1/done', 0)]

client_id = 'img_gen_1'

data = []


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
    img = io.BytesIO()
    time_sent = []
    def on_message(client, userdata, msg):
        print("Recieved data from {} topic".format(msg.topic))
        if (msg.topic == 'edge/cam/1*'):
            print("Recieved from first topic")
        # print("Data : {}".format(msg.payload))
        print("Lenght : {}".format(len(msg.payload)))
        if(msg.topic == topic[0][0]):
            time_sent.append(msg.payload.decode())
            print(f"The time is ... {time_sent}")
            img.seek(0)
            img.truncate()
        elif(msg.topic == topic[1][0]):
            # data.append(msg.payload)
            img.seek(0, 2)
            img.write(msg.payload)
            print("inprogress...")
            print(img.getbuffer().nbytes)
        elif(msg.topic == topic[2][0]):
            print("===DONE===")
            # data.append(msg.payload)
            img.seek(0, 2)
            img.write(msg.payload)
            img.seek(0)
            print(time_sent[0])
            print("do somethink here")
            # b_data = b''.join(data)
            time_sent.clear()
            # data.clear()
            # print(b_data)
            print(img.getbuffer().nbytes)
            print(len(time_sent))
            # img_data = io.BytesIO(b_data)
            im = Image.open(img)
            t_dir = get_dir()
            time_now = time.strftime("%Y-%m-%d")
            img_name = "{}_{}.jpeg".format(random.randint(1111, 9999), time_now)
            img_path = os.path.join(t_dir, img_name)
            im.save(img_path)
            if os.path.exists(img_path):
                print(img_name, "saved succesfully")
    client.subscribe(topic)
    client.on_message = on_message


def run():
    print("Subscriber with id {} is running....".format(client_id))
    get_dir()
    client = connect_mqtt()
    subscribe_mqtt(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
