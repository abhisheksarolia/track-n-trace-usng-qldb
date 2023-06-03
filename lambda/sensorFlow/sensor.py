from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
import json
import os

received_all_event = threading.Event()

target_ep = 'Add your AWS IoT Core endpoint here'
thing_name = 'trackntraceSensor'
cert_filepath = './certificate.pem'
private_key_filepath = './privateKey.pem'
ca_filepath = './AmazonRootCA1.pem'

#pub_topic = 'device/{}/data'.format(thing_name)
pub_topic = 'trkntrcesensortopic'
#sub_topic = 'app/{}/data'.format(thing_name)

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))

# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

proxy_options = None

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=target_ep,
    port=8883,
    cert_filepath=cert_filepath,
    pri_key_filepath=private_key_filepath,
    client_bootstrap=client_bootstrap,
    ca_filepath=ca_filepath,
    on_connection_interrupted=on_connection_interrupted,
    # on_connection_resumed=on_connection_resumed,
    client_id=thing_name,
    clean_session=True,
    keep_alive_secs=30,
    http_proxy_options=proxy_options)

print("Connecting to {} with client ID '{}'...".format(
    target_ep, thing_name))

# Connect to the Gateway
try:
    connect_future = mqtt_connection.connect()
    # Future.result() waits until a result is available
    connect_future.result()
except Exception as e:
    print("Connection to IoT Core failed - {}".format(e))
else:
    print("Connected!")


print ('Publishing message on topic {}'.format(pub_topic))

message_data ={
    "data": 12,
    "package": "MFGPKG1",
    "batch": "ZAX42H"
}

message_json = json.dumps(message_data)

try:
    mqtt_connection.publish(
    topic=pub_topic,
    payload=message_json,
    qos=mqtt.QoS.AT_LEAST_ONCE)
except Exception as e:
    print("Publish failed - {}".format(e))
