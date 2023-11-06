import sys
import io
import tensorflow as tf
import os
import asyncio
import requests
import time
from models import decoder, prediction_head
from utils import data_utils, draw_utils
from firebase_admin import credentials, initialize_app, storage
from paho.mqtt import client as mqtt_client
from PIL import Image, ImageDraw
from telegram import Bot
from telegram.ext import MessageHandler, ContextTypes

LABELS = ["BG", "Human"]

ID = 1
client_id = "edge_{}".format(ID)
topic = [(f"edge/cam/{ID}/time", 0), (f"edge/cam/{ID}/inprogress", 0), (f"edge/cam/{ID}/done", 0)]
broker_address = "192.168.72.119"
port = 1883

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "d:\keys\cloud-mqtt-detection-firebase-adminsdk-s4wo7-fe9e91fb67.json"  # add your Credentials keys path to sys environtment

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
with open("telegram_key.txt") as f:
    token = f.readline()
base_url = f"https://api.telegram.org/bot{token}/sendPhoto"


def model_init() -> tf.keras.Model:
    working_dir = os.getcwd()
    model_dir = os.path.join(working_dir, "model")
    blob_name = "12_2023-11-02_mobilenet_v2_Id-88.h5"
    model_path = os.path.join(model_dir, blob_name)
    if not os.path.exists(model_dir):
        print("no model found, downloading from the internet ...")
        os.makedirs(model_dir)
        initialize_app(credential=cred)
        bucket = storage.bucket(name="cloud-mqtt-detection.appspot.com")
        blob = bucket.blob(blob_name=blob_name)
        blob.download_to_filename(model_path)
        print("download success")
    print("loading the model")
    model = tf.keras.models.load_model(model_path, compile=False)
    return model

def data_logging(size, time_sent, time_arrive, time_edge_sent):
    delay = 0
    date_now = time.strftime("%Y-%m-%d", time.localtime())
    working_dir = os.getcwd()
    log_dir = os.path.join(working_dir, "log")
    file_name = "{}_{}_subscriber.txt".format(date_now, client_id)
    file_path = os.path.join(log_dir, file_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if not os.path.exists(file_path):
        print("hereee")
        with open(file_path, 'a') as f:
            print("size(byte),time_sent,time_arrive,time_edge_sent", file=f)
    with open(file_path, 'a') as f:
        print("{},{},{},{}".format(size, time_sent, time_arrive, time_edge_sent), file=f)
    print('calculate')
    print(time_sent)
    print(time_arrive)
    print(time_edge_sent)
    


def connect_mqtt() -> mqtt_client:
    print(f"connecting to {broker_address}")

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("{} connected to MQTT Broker!".format(client_id))
        else:
            print("Failed to connect with return code {}".format(rc))

    client = mqtt_client.Client(client_id=client_id)
    client.on_connect = on_connect
    client.connect(broker_address, port)
    return client


def subscribe_mqtt(client: mqtt_client, ssd_model: tf.keras.Model):
    img = io.BytesIO()
    time_sent = []

    def on_message(client, userdata, msg):
        # print("Recieved data from {} topic".format(msg.topic))
        # print("Lenght : {}".format(len(msg.payload)))
        if msg.topic == topic[0][0]:
            time_sent.append(msg.payload.decode())
            print(f"The time is ... {time_sent}")
            img.seek(0)
            img.truncate()
            time_arv = time.strftime("%H:%M:%S", time.localtime())
            time.sleep(3)
            time_edge_sent = time.strftime("%H:%M:%S", time.localtime())
            
            data_logging(10 ,time_sent[0], time_arv, time_edge_sent)
            time_sent.clear()
        elif msg.topic == topic[1][0]:
            img.seek(0, 2)
            img.write(msg.payload)
            # print("inprogress...")
            # print(img.getbuffer().nbytes)
        elif msg.topic == topic[2][0]:
            print("===DONE===")
            # data.append(msg.payload)
            img.seek(0, 2)
            img.write(msg.payload)
            img.seek(0)
            print(img.getbuffer().nbytes)
            print(len(time_sent))
            data = data_utils.single_custom_data_gen(img, 500, 500)
            p_bbox, p_scores, p_labels = ssd_model.predict(data)
            data = tf.squeeze(data)
            p_bbox = tf.squeeze(p_bbox)
            p_scores = tf.squeeze(p_scores)
            p_labels = tf.squeeze(p_labels)
            image = draw_utils.infer_draw_predictions(
                data, p_bbox, p_labels, p_scores, LABELS, return_img=True
            )
            if any(i >= 0.7 for i in p_scores):
                pred_img = io.BytesIO()
                pred_img.name = "result.jpeg"
                image.save(pred_img, "JPEG")
                pred_img.seek(0)
                parameter = {}
                files = {}
                files["photo"] = pred_img
                parameter["chat_id"] = "-1001974152494"  # id of channel telegram
                # parameter["photo"] = image_path
                parameter["caption"] = time_sent[0]
                time_sent.clear()
                print(base_url)
                print(parameter)
                resp = requests.post(base_url, params=parameter, files=files)
                print(resp.status_code)
            else:
                time_sent.clear()
                print("no human found")

    client.subscribe(topic)
    client.on_message = on_message


def main():
    model = model_init()
    client = connect_mqtt()
    subscribe_mqtt(client, model)
    client.loop_forever()


if __name__ == "__main__":
    main()
