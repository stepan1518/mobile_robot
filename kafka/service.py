import json
import threading
import logging
from typing import List, Optional
from confluent_kafka import Consumer, KafkaError, TopicPartition
from .observer import MessageObserver

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    """
    Фоновый потребитель Kafka с уведомлением подписчиков по типу сообщения.
    """

    def __init__(self, consumer: Consumer, topics: List[str]):
        self.consumer = consumer
        self.topics = topics
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._observers: dict[str, List[MessageObserver]] = {}
        self._lock = threading.Lock()

    def register_observer(self, msg_type: str, observer: MessageObserver):
        with self._lock:
            self._observers.setdefault(msg_type, []).append(observer)
        logger.info(f"[KafkaService] Observer registered: type='{msg_type}'")

    def unregister_observer(self, msg_type: str, observer: MessageObserver):
        with self._lock:
            if msg_type in self._observers:
                try:
                    self._observers[msg_type].remove(observer)
                    if not self._observers[msg_type]:
                        del self._observers[msg_type]
                    logger.info(f"[KafkaService] Observer unregistered: type='{msg_type}'")
                except ValueError:
                    pass

    def start(self, seek_back_seconds: int = 0):
        if self.running:
            return
        self.consumer.subscribe(self.topics)
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="KafkaObserver")
        self._thread.start()
        logger.info(f"[KafkaService] Started. Topics: {self.topics}")

    def stop(self, timeout: float = 10.0):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        if self.consumer:
            self.consumer.close()
        logger.info("[KafkaService] Stopped.")

    def _run(self):
        try:
            while self.running:
                msg = self.consumer.poll(1.0)
                self.consumer.commit(message=msg)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Kafka error: {msg.error()}")
                    continue
                self._process_message(msg)
        except Exception as e:
            logger.exception(f"Consumer loop error: {e}")

    def _process_message(self, msg):
        try:
            self.consumer.commit()
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            return
        self._notify_observers(msg)

    def _notify_observers(self, msg):
        msg_type, value = self._extract_json_and_message_type(msg)
        with self._lock:
            observers = list(self._observers.get(msg_type, []))
            observers.extend(self._observers.get('*', []))
        for observer in observers:
            try:
                observer.on_message(value)
            except Exception as e:
                logger.error(f"Observer {observer} failed at offset {msg.offset()}: {e}")

    def _extract_json_and_message_type(self, msg) -> (str, dict):
        try:
            data = json.loads(msg.value().decode('utf-8'))
            return data.get('object_type', '__unknown__'), data
        except Exception:
            pass
        return '__unknown__', {}