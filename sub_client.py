import sys
import io
import tensorflow as tf
import os
import asyncio
from models import decoder, prediction_head
from utils import data_utils
from firebase_admin import credentials, initialize_app, storage
from paho.mqtt import client as mqtt_client
from PIL import Image, ImageDraw
from telegram import Bot
from telegram.ext import MessageHandler, ContextTypes

broker_address = '192.168.100.2'
port = 1883
topic = [('edge/cam/1', 0), ('edge/cam/2', 0)]

client_id = 'edge_1'

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) # add your Credentials keys path to sys environtment
image_path = "D:\\1.Skripsi\\Edge\\img\\2023-07-28_4473.jpeg"
with open("telegram_key.txt") as f:
    token = f.readline()


def model_init() -> tf.keras.Model:
    working_dir = os.getcwd()
    model_dir = os.path.join(working_dir, 'model')
    blob_name = "vgg16_Id-32_2023-09-20.h5"
    model_path = os.path.join(model_dir, blob_name)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        initialize_app(credential=cred)
        bucket = storage.bucket(name="cloud-mqtt-detection.appspot.com")
        blob = bucket.blob(blob_name=blob_name)
        blob.download_to_filename(model_path)
        print('download success')
    model = tf.keras.models.load_model(model_path, compile=False)
    return model
    # model_path = m_path

def denormalize_bboxes(bboxes, height, width):
    """Denormalizing bounding boxes.
    Args:
        bboxes : (batch_size, total_bboxes, [ymin, xmin, ymax, xmax])
            in normalized form [0, 1]
        height : image height
        width : image width

    Returns:
        denormalized_bboxes : (batch_size, total_bboxes, [ymin, xmin, ymax, xmax])
    """
    ymin = bboxes[..., 0] * height
    xmin = bboxes[..., 1] * width
    ymax = bboxes[..., 2] * height
    xmax = bboxes[..., 3] * width
    return tf.round(tf.stack([ymin, xmin, ymax, xmax], axis=-1))

def draw_bboxes_with_labels(img, bboxes, label_indices, probs, labels):
    """Drawing bounding boxes with labels on given image.
    inputs:
        img : (height, width, channels)
        bboxes : (total_bboxes, [y1, x1, y2, x2])
            in denormalized form
        label_indices : (total_bboxes)
        probs : (total_bboxes)
        labels : [labels string list]
    """
    colors = tf.random.uniform((len(labels), 4), maxval=256, dtype=tf.int32)
    image = tf.keras.preprocessing.image.array_to_img(img)
    draw = ImageDraw.Draw(image)
    for index, bbox in enumerate(bboxes):
        y1, x1, y2, x2 = tf.split(bbox, 4)
        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            continue
        label_index = int(label_indices[index])
        color = tuple(colors[label_index].numpy())
        label_text = "{0} {1:0.3f}".format(labels[label_index], probs[index])
        draw.text((x1 + 1, y1 - 11), label_text, fill=color)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
    #
    # do something with image variable ie image.show()

def infer_draw_predictions(imgs, pred_bboxes, pred_labels, pred_scores, labels):
    img_size = imgs.shape[1]
    # for i, img in enumerate(imgs):
    denormalized_bboxes = denormalize_bboxes(pred_bboxes, img_size, img_size)
    draw_bboxes_with_labels(imgs, denormalized_bboxes, pred_labels, pred_scores, labels)

def send_photo_telegram(imgs, caption):
    bot = Bot(token=token)
    print("sending..")
    caption = "test"
    bot.send_message(text="asdasd")
    bot.send_photo(photo=imgs, caption=caption)


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

def subscribe_mqtt(client: mqtt_client, ssd_model: tf.keras.Model, jj):
    def on_message(client, userdata, msg):
        print("Recieved data from {} topic".format(msg.topic))
        if (msg.topic == 'edge/cam/1'):
            print("Recieved from first topic")
        print("Data : {}".format(msg.payload))
        print("Lenght : {}".format(len(msg.payload)))
        tes = io.BytesIO(msg.payload)
        data = data_utils.single_custom_data_gen(image_path, 300, 300)
        send_photo_telegram(image_path, "test")
        p_bbox, p_scores, p_labels = ssd_model.predict(data)
        p_bbox = tf.squeeze(p_bbox)
        p_scores = tf.squeeze(p_scores)
        p_labels = tf.squeeze(p_labels)
        print(any(i >= 0.8 for i in p_scores))


    client.subscribe(topic)
    client.on_message = on_message

def main():
    model = model_init()
    client = connect_mqtt()
    subscribe_mqtt(client, model, False)
    client.loop_forever()

if __name__ == '__main__':
    asyncio.run(main())
