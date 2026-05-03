from abc import ABC, abstractmethod


class MessageObserver(ABC):
    """Подписчик на сообщения Kafka."""

    @abstractmethod
    def on_message(self, message):
        """
        Вызывается при получении подходящего сообщения.
        :param message: сырой объект confluent_kafka.Message
        """
        ...