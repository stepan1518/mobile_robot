import json
import uuid
from abc import abstractmethod
from datetime import datetime

from kafka.producer import KafkaProducerService


class UUIDGenerator:
    @staticmethod
    def generate():
        return str(uuid.uuid7())

class KafkaMessageHandler:
    @abstractmethod
    def handle(self, message):
        pass


class ProducerMessageHandler(KafkaMessageHandler):
    def __init__(self, producer : KafkaProducerService, topic, conf_version):
        self.producer = producer
        self.conf_version = conf_version
        self.topic = topic

    def handle(self, message):
        dct, id = self.to_dict(message)
        jsn = self.to_json(dct)
        self.producer.send(self.topic, jsn, key=id)

    def to_dict(self, message):

        id = message.get("id", UUIDGenerator.generate())
        creation_time = message.get("timestamp", None)
        current_time = datetime.now().isoformat()

        return {
            "id": id,
            "creation_time": creation_time,
            "current_time": current_time,
            "detection_class_type":  message.get('object_type', '__unknown__'),
            "configuration_id" : self.conf_version
        }, id

    def to_json(self, dct):
        return json.dumps(dct, ensure_ascii=False)