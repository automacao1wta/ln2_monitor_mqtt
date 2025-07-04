import paho.mqtt.client as mqtt
import yaml
from logger_config import setup_logger
import threading
from queue import Queue
from datetime import datetime

# Load constants from config file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
CLIENT_ID = config['client']['client_id']
CLIENT_USERNAME = config['client']['username']
CLIENT_PASSWORD = config['client']['password']
BROKER_HOST = config['broker']['host']
BROKER_PORT = config['broker']['port']
TOPICS = config['topics']

class MessageSubscriber:
    def __init__(self, message_queue: Queue) -> None:            
        self.client = self.create_client()
        self.logger = setup_logger(__name__)
        self.connect_thread = threading.Thread(target=self.connect_client)
        self.message_queue = message_queue


    def create_client(self) -> mqtt.Client:
        client = mqtt.Client(client_id=CLIENT_ID)
        client.username_pw_set(CLIENT_USERNAME, CLIENT_PASSWORD)
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        return client
    

    def connect_client(self) -> None:
        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self.logger.info("Client connected to broker")
        except Exception as e:
            self.logger.error("Failed to connect to broker: %s", e)


    def subscribe_to_topics(self):
        for topic in TOPICS:
            self.client.subscribe(topic, qos=1)
            self.logger.info("Subscribed to topic: %s", topic)


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to broker with result code: %s", rc)
            self.subscribe_to_topics()  # Subscribe to topics upon successful connection
        else:
            self.logger.error("Failed to connect to broker with result code: %s", rc)


    def on_message(self, client:mqtt.Client, userdata, message:mqtt.MQTTMessage):
        message_timestamp = datetime.now()

        self.logger.debug("Received message from topic: %s, payload: %s", message.topic, message.payload)

        message_tuple = (message_timestamp, message)

        try:
            self.message_queue.put(message_tuple)
        except Exception as e:
            self.logger.error("Failed to put message on queue: %s", e)

    
    def run(self):
        self.connect_client()
        self.client.loop_forever(retry_first_connection=True)