from abc import ABC, abstractmethod
import threading
import json
import logging

class MessageObserver(ABC):
    """Подписчик на сообщения Kafka."""

    @abstractmethod
    def on_message(self, message):
        """
        Вызывается при получении подходящего сообщения.
        :param message: сырой объект confluent_kafka.Message
        """

logger = logging.getLogger(__name__)


class WaitTrafficLightObserver(MessageObserver):
    """
    Наблюдатель за состоянием светофора.

    При получении сообщения типа 'traffic_light' меняет внутренний флаг.
    Потокобезопасен: чтение/запись защищены блокировкой.

    Использование:
        light = WaitTrafficLightObserver()
        service.register_observer('traffic_light', light)

        # В основном потоке робота:
        if light.is_green():
            move_forward()
    """

    def __init__(self):
        self._green = False
        self._lock = threading.Lock()

    def on_message(self, message):
        """
        Ожидает JSON с полем 'state': 'green' или 'red'.
        """
        state = 'RED'
        try:
            state = message.get('data', {}).get('color', 'RED')
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"TrafficLightObserver: bad message at offset {message.offset()}: {e}")
            return

        if state == 'GREEN':
            with self._lock:
                self._green = True
    def is_green(self) -> bool:
        """Потокобезопасное чтение текущего состояния светофора."""
        with self._lock:
            return self._green