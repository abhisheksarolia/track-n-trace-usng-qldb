# /*
#  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  * SPDX-License-Identifier: MIT-0
#  *
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  * software and associated documentation files (the "Software"), to deal in the Software
#  * without restriction, including without limitation the rights to use, copy, modify,
#  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  * permit persons to whom the Software is furnished to do so.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#  */

# Processing functionality to simulate sensor flow message push to AWS IoT Core as MQTT message

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
pub_topic = 'trkntrcesensortopic'

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
    client_id=thing_name,
    clean_session=True,
    keep_alive_secs=30,
    http_proxy_options=proxy_options)

print("Connecting to {} with client ID '{}'...".format(
    target_ep, thing_name))

# Connect to the Gateway
try:
    connect_future = mqtt_connection.connect()
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