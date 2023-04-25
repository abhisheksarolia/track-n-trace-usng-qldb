# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import sys
import threading
import time
import json
import os

received_all_event = threading.Event()

target_ep = 'a2my7mzgrt2ewd-ats.iot.us-east-1.amazonaws.com'
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


# # Callback when an interrupted connection is re-established.
# def on_connection_resumed(connection, return_code, session_present, **kwargs):
#     print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

#     if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
#         print("Session did not persist. Resubscribing to existing topics...")
#         resubscribe_future, _ = connection.resubscribe_existing_topics()

#         # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
#         # evaluate result with a callback instead.
#         resubscribe_future.add_done_callback(on_resubscribe_complete)


# def on_resubscribe_complete(resubscribe_future):
#     resubscribe_results = resubscribe_future.result()
#     print("Resubscribe results: {}".format(resubscribe_results))

#     for topic, qos in resubscribe_results['topics']:
#         if qos is None:
#             sys.exit("Server rejected resubscribe to topic: {}".format(topic))
                
# # Callback when the subscribed topic receives a message
# def on_message_received(topic, payload, dup, qos, retain, **kwargs):
#     print("Received message from topic '{}': {}".format(topic, payload))

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

#Connect to the gateway
# while True:
#   try:
#     connect_future = mqtt_connection.connect()
# # Future.result() waits until a result is available
#     connect_future.result()
#   except Exception as e:
#     print("Connection to IoT Core failed...  retrying in 5s.- {}".format(e))
#     time.sleep(5)
#     continue
#   else:
#     print("Connected!")
#     break

# #Subscribe
# print("Subscribing to topic " + sub_topic)
# subscribe_future, packet_id = mqtt_connection.subscribe(
#     topic=sub_topic,
#     qos=mqtt.QoS.AT_LEAST_ONCE,
#     callback=on_message_received)

# subscribe_result = subscribe_future.result()
# print("Subscribed with {}".format(str(subscribe_result['qos'])))

# Connect to the Gateway
try:
    connect_future = mqtt_connection.connect()
    # Future.result() waits until a result is available
    connect_future.result()
except Exception as e:
    print("Connection to IoT Core failed...  retrying in 5s.- {}".format(e))
else:
    print("Connected!")


print ('Publishing message on topic {}'.format(pub_topic))

temp=12
message_data ={
    "temperature": 12,
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
