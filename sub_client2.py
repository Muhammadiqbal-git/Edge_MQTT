import io
import os
import json
import requests
import time
import random
import tensorflow as tf

from models import decoder, prediction_head
from utils import data_utils, draw_utils
from firebase_admin import credentials, initialize_app, storage
from paho.mqtt import client as mqtt_client
from PIL import Image, ImageFile


LABELS = ["BG", "Human"]

ID = 2
client_id = "edge_{}".format(ID)
topic = [
    (f"edge/cam/{ID}/time", 0),
    (f"edge/cam/{ID}/inprogress", 0),
    (f"edge/cam/{ID}/done", 0),
]
broker_address = "192.168.196.119"
port = 1883

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "d:\keys\cloud-mqtt-detection-firebase-adminsdk-s4wo7-fe9e91fb67.json"  # add your Credentials keys path to sys environtment

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
with open("telegram_key.txt") as f:
    token = f.readline()
base_url = "https://api.telegram.org/bot{}/sendPhoto".format(token)


def model_init() -> tf.keras.Model:
    working_dir = os.getcwd()
    model_dir = os.path.join(working_dir, "model")
    blob_name = "22_2023-11-22_mobilenet_v2_ID-29.h5"
    model_path = os.path.join(model_dir, blob_name)
    if not os.path.exists(model_path):
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        print("no model found, downloading from the internet ...")
        initialize_app(credential=cred)
        bucket = storage.bucket(name="cloud-mqtt-detection.appspot.com")
        blob = bucket.blob(blob_name=blob_name)
        blob.download_to_filename(model_path)
        print("download success")
    print("loading the model")
    model = tf.keras.models.load_model(model_path, compile=False)
    return model


def data_logging(
    size, cam_time_sent, edge_time_arrival, edge_time_sent, telegram_time_arrival
):
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
        with open(file_path, "a") as f:
            print(
                "size(byte),cam_time_sent,edge_time_arv,edge_time_sent,telegram_time_arv",
                file=f,
            )
    with open(file_path, "a") as f:
        print(
            "{},{},{},{},{}".format(
                size,
                cam_time_sent,
                edge_time_arrival,
                edge_time_sent,
                telegram_time_arrival,
            ),
            file=f,
        )


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

def cache_data(edge_time_sent, img_data):
    data_cache = {}
    time_cached = time.strftime("%Y-%m-%d")
    working_dir = os.getcwd()
    cache_dir = os.path.join(working_dir, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    img_fname = "{}_{}_CAM-{}_{}.jpeg".format(
        time_cached,
        edge_time_sent.replace(":", "-"),
        ID,
        random.randint(1111, 9999),
    )
    json_fname = img_fname.replace(".jpeg", ".json")
    img_cache_path = os.path.join(cache_dir, img_fname)
    data_cache_path = os.path.join(cache_dir, json_fname)
    data_cache["cam_id"] = ID
    data_cache["cache_time"] = edge_time_sent
    data_cache["cache_date"] = time_cached
    data_cache["img_path"] = img_cache_path
    img_data.save(img_cache_path, format="JPEG")
    with open(data_cache_path, "w") as f:
        json.dump(data_cache, f)
    
    


def subscribe_mqtt(client: mqtt_client, ssd_model: tf.keras.Model):
    img = io.BytesIO()
    cam_time_sent = []

    def on_message(client, userdata, msg):
        # print("Recieved data from {} topic".format(msg.topic))
        # print("Lenght : {}".format(len(msg.payload)))
        if msg.topic == topic[0][0]:
            cam_time_sent.clear()
            cam_time_sent.append(msg.payload.decode())
            print(f"The time is ... {cam_time_sent}")
            img.seek(0)
            img.truncate()
        elif msg.topic == topic[1][0]:
            img.seek(0, 2)
            img.write(msg.payload)
        elif msg.topic == topic[2][0]:
            print("===DONE===")
            img.seek(0, 2)
            img.write(msg.payload)
            img.seek(0)
            edge_time_arv = time.strftime("%H:%M:%S", time.localtime())
            print("time {}".format(edge_time_arv))
            print(img.getbuffer().nbytes)
            print(len(cam_time_sent))
            data = data_utils.single_custom_data_gen(img, 500, 500)
            p_bbox, p_scores, p_labels = ssd_model.predict(data)
            result_img = draw_utils.infer_draw_predictions(
                data, p_bbox, p_labels, p_scores, LABELS, return_img=True
            )
            print(f"type {type(result_img)}")
            if any(i >= 0.7 for i in tf.squeeze(p_scores)): # IF any confidence scores is more than 0.7 (likely there is human)
                # if True:
                print("human detected")
                buff_result_img = io.BytesIO()
                buff_result_img.name = "result.jpeg"
                result_img.save(buff_result_img, "JPEG")
                buff_result_img.seek(0)
                parameter = {}
                files = {}
                files["photo"] = buff_result_img
                parameter["chat_id"] = "-1001974152494"  # id of channel telegram
                parameter["caption"] = "{}\nLocation: CAM-{}".format(cam_time_sent[0], ID)
                print(base_url)
                print(parameter)
                edge_time_sent = time.strftime("%H:%M:%S", time.localtime())
                try:
                    resp = requests.post(base_url, params=parameter, files=files, timeout=4)
                    print(resp.status_code)
                    if resp.status_code == 200:
                        telegram_time_arrival = time.strftime(
                            "%H:%M:%S", time.localtime()
                        )
                        data_logging(
                            img.getbuffer().nbytes,
                            cam_time_sent[0],
                            edge_time_arv,
                            edge_time_sent,
                            telegram_time_arrival,
                        )
                    else:
                        raise Exception("other than 200")
                except:
                    cache_data(edge_time_sent, result_img)

            else:
                cam_time_sent.clear()
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
