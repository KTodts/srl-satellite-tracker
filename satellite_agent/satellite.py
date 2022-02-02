#!/usr/bin/env python
# coding=utf-8
import urllib.request
import netns

import grpc
import datetime
import sys
import logging
import socket
import os
import ipaddress
import signal
import time
import threading
import json

import sdk_service_pb2
import sdk_service_pb2_grpc
import sdk_common_pb2
import config_service_pb2
import telemetry_service_pb2
import telemetry_service_pb2_grpc

############################################################
## Agent will start with this name
############################################################
agent_name = 'satellite'
metadata = [('agent_name', agent_name)]

############################################################
## Global parameters:
## Open a GRPC channel to connect to the SR Linux sdk_mgr
## sdk_mgr will be listening on 50053
## and create an SDK service client stub
############################################################

channel = grpc.insecure_channel('127.0.0.1:50053')
stub = sdk_service_pb2_grpc.SdkMgrServiceStub(channel)
sdk_notification_service_client = sdk_service_pb2_grpc.SdkNotificationServiceStub(channel)

## Verify that SIGTERM signal was received
sigterm_exit = False
interval = 10

############################################################
## Gracefully handle SIGTERM signal (SIGTERM number = 15)
## When called, will unregister Agent and gracefully exit
############################################################
def exit_gracefully(signum, frame):
    logging.info("Caught signal :: {}\n will unregister satellite agent".format(signum))
    try:
        # Set global sigterm_exit to true
        global sigterm_exit
        sigterm_exit = True
        logging.info(f"Unregister Agent")

        # Unregister agent
        unregister_request = sdk_service_pb2.AgentRegistrationRequest()
        unregister_response = stub.AgentUnRegister(request=unregister_request, metadata=metadata)
        logging.info(f"Unregister response:: {sdk_common_pb2.SdkMgrStatus.Name(unregister_response.status)}")
    except grpc._channel._Rendezvous as err:
        logging.error('GOING TO EXIT NOW: {}'.format(err))
        sys.exit()

## Keep Alive thread: send a keep every 10 seconds via gRPC call
def send_keep_alive():
    ## exit the thread when sigterm is received
    while not sigterm_exit:
        global interval
        logging.info("Send Keep Alive")
        keepalive_request = sdk_service_pb2.KeepAliveRequest()
        keepalive_response = stub.KeepAlive(request=keepalive_request, metadata=metadata)
        if keepalive_response.status == sdk_common_pb2.SdkMgrStatus.Value("kSdkMgrFailed"):
            logging.error("Keep Alive failed")
        time.sleep(10)

#####################################
## Create an SDK notification stream
#####################################
def create_sdk_stream():

    # build Create request
    op = sdk_service_pb2.NotificationRegisterRequest.Create
    request=sdk_service_pb2.NotificationRegisterRequest(op=op)

    # call SDK RPC to create a new stream
    notification_response = stub.NotificationRegister(
        request=request,
        metadata=metadata)

    # process the response, return stream ID if successful
    if notification_response.status == sdk_common_pb2.SdkMgrStatus.Value("kSdkMgrFailed"):
        logging.error(f"Notification Stream Create failed with error {notification_response.error_str}")
        return 0
    else:
        logging.info(f"Notification Stream successful. stream ID: {notification_response.stream_id}, sub ID: {notification_response.sub_id}")
        return notification_response.stream_id


#########################################################
## Use notification stream to subscribe to 'config events
#########################################################
def add_sdk_config_subscription(stream_id):

    # Build subscription request for config events
    subs_request=sdk_service_pb2.NotificationRegisterRequest(
        op=sdk_service_pb2.NotificationRegisterRequest.AddSubscription,
        stream_id=stream_id,
        config=config_service_pb2.ConfigSubscriptionRequest())

    # Call RPC
    subscription_response = stub.NotificationRegister(
        request=subs_request,
        metadata=metadata)


    # Process response
    if subscription_response.status == sdk_common_pb2.SdkMgrStatus.Value("kSdkMgrFailed"):
        logging.error("Config Subscription failed")
    else:
        logging.info(f"Config Subscription successful. stream ID: {subscription_response.stream_id}, sub ID: {subscription_response.sub_id}")
    return

########################################################
## Start notification stream from SDK SR Linux
#########################################################
def start_notification_stream(stream_id):
    # Build request
    request=sdk_service_pb2.NotificationStreamRequest(stream_id=stream_id)

    # Call Server Streaming SDK service
    # SR Linux will start streamning requested notifications
    notification_stream = sdk_notification_service_client.NotificationStream(
        request=request,
        metadata=metadata)

    logging.info("Start notification stream :: {notification_stream}")
    # return the stream
    return notification_stream

########################################################
## Process the received notification stream
## Only config events are expected
## Exit the loop if SIGTERM is received
#########################################################
def process_notification(notification):
    for obj in notification.notification:
        if obj.HasField("config"):
            ## Process config notification
            logging.info("--> Received config notification")
            process_config_notification(obj)
        else:
            logging.info("--> Received unexpected notification")
        if sigterm_exit:
            ## exit loop if agent has been stopped
            logging.info("Agent Stopped Time :: {}".format(datetime.datetime.now()))
            return

########################################################
## Process specifically a config notification
## Expects that 'interval' from 'satellite' branch has been configured
## Will set 'response' string as a response
#########################################################
def process_config_notification(obj):

    # Convert received JSON string into a dictionary
    data = json.loads(obj.config.data.json)
    logging.info(f"Data :: {data}" )

    # Check if the expected 'name' filed is present
    if 'interval' in data:

        # extract its value from dictionary
        global interval
        interval = data['interval']['value']


############################################################
## update a object in the state datastore
## using the telemetry grpc service
## Input parameters:
## - js_path: JSON Path = the base YANG container
## - js_data: JSON attribute/value pair(s) based on the YANG model
############################################################
def update_state_datastore( js_path, js_data ):

    # create gRPC client stub for the Telemetry Service
    telemetry_stub = telemetry_service_pb2_grpc.SdkMgrTelemetryServiceStub(channel)

    # Build an telemetry update service request
    telemetry_update_request = telemetry_service_pb2.TelemetryUpdateRequest()

    # Add the YANG Path and Attribute/Value pair to the request
    #for js_path,js_data in path_obj_list:
    telemetry_info = telemetry_update_request.state.add()
    telemetry_info.key.js_path = js_path
    telemetry_info.data.json_content = js_data

    # Log the request
    logging.info(f"Telemetry_Update_Request ::\n{telemetry_update_request}")

    # Call the telemetry RPC
    telemetry_response = telemetry_stub.TelemetryAddOrUpdate(
        request=telemetry_update_request,
        metadata=metadata)

    return telemetry_response

## Fetch data with http request.
def http_request(url):
    # switch namespace when making http request
    with netns.NetNS(nsname="srbase-mgmt"):
        response = urllib.request.urlopen(url).read()
    
    data = response.decode('utf-8')
    data = json.loads(data)
    return data

## Get satellite data thread: fetch data every X seconds. X defined by user. default 10 seconds
def get_satellite_data():
    ## exit the thread when sigterm is received
    while not sigterm_exit:
        ## make the http request 
        url = "https://api.wheretheiss.at/v1/satellites/25544"
        response = http_request(url)

        # Convert dict to a dict TelemtryUpdateRequests understands
        data = {k:{"value":str(v)} for k,v in response.items()}
        logging.info(f"DATA for Telemetry :: {data}")

        ## Update State datastore
        logging.info(f"name         = {response['name']}")
        logging.info(f"id           = {response['id']}")
        logging.info(f"latitude     = {response['latitude']}")
        logging.info(f"longitude    = {response['longitude']}")
        logging.info(f"altitude     = {response['altitude']}")
        logging.info(f"velocity     = {response['velocity']}")
        logging.info(f"visibility   = {response['visibility']}")
        logging.info(f"footprint    = {response['footprint']}")
        logging.info(f"timestamp    = {response['timestamp']}")
        logging.info(f"daynum       = {response['daynum']}")
        logging.info(f"solar_lat    = {response['solar_lat']}")
        logging.info(f"solar_lon    = {response['solar_lon']}")
        logging.info(f"units        = {response['units']}")

        update_state_datastore( js_path='.satellite',js_data=json.dumps(data))
    
        # Set sample interval
        global interval
        time.sleep(float(interval))

## Agent function
def run_agent():

    ## Build register agent request
    register_request = sdk_service_pb2.AgentRegistrationRequest()
    register_request.agent_liveliness=10

    ## Call AgentRegister RPC
    register_response = stub.AgentRegister(request=register_request, metadata=metadata)

    ## Process AgentRegister response
    if register_response.status == sdk_common_pb2.SdkMgrStatus.Value("kSdkMgrFailed"):
        logging.error(f"Agent Registration failed with error {register_response.error_str}")
    else:
        logging.info(f"Agent Registration successful. App ID: {register_response.app_id}")

     ## Start separate thread to send keep alive every 10 seconds
    thread = threading.Thread(target=send_keep_alive)
    thread.start()

    ## Start separate thread to fetch satellite data every X seconds
    thread2 = threading.Thread(target=get_satellite_data)
    thread2.start()

    ## Create a new SDK notification stream
    stream_id = create_sdk_stream()
    
    ## Subscribe to 'config' notifications
    ## Only configuration of satellite YANG data models will be received
    add_sdk_config_subscription(stream_id)

    ## Start listening for notifications from SR Linux
    notification_stream  = start_notification_stream(stream_id)

    ## process received notifications
    for notification in notification_stream:
        process_notification(notification)

			
if __name__ == '__main__':

    ## configure SIGTERM handler
    signal.signal(signal.SIGTERM, exit_gracefully)

    ## configure log file
    log_filename = '/var/log/srlinux/stdout/hello-satellite.log'
    logging.basicConfig(filename=log_filename, filemode='w',datefmt='%H:%M:%S', level=logging.INFO)
    logging.info("Agent Start Time :: {}".format(datetime.datetime.now()))

    ## Run agent function
    run_agent()
    sys.exit()
