import time

from paho.mqtt import client as mqtt_client

broker_address = '192.168.100.2'
port = 1883
topic = 'edge/cam/1'

client_id = 'cam_1'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print('Connected to MQTT broker')
        else:
            print('Failed to connect with return code {}'.format(rc))
    client = mqtt_client.Client(client_id=client_id)
    client.on_connect = on_connect
    client.connect(broker_address, port)
    return client

def publish(client, msg):
    result = client.publish(topic, msg)

    if result[0] == 0:
        print('Message sent to {}'.format(topic))
    else:
        print('Failed to send message to {}'.format(topic))

def run():
    client = connect_mqtt()
    client.loop_start()
    data = 'data test'
    publish(client, data)
    client.loop_stop()

if __name__ == '__main__':
    run()
