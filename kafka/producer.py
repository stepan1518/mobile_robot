from confluent_kafka import Producer

class KafkaProducerService:
    """Сервис для отправки DetectionResult в Kafka."""

    def __init__(self, bootstrap_servers: str, client_id: str):
        self._producer = Producer({
            'bootstrap.servers': bootstrap_servers,
            'client.id': client_id,
            'acks': '1',
            'retries': 3,
            'linger.ms': 5,
            'compression.type': 'zstd',
            'queue.buffering.max.messages': 100000,
            'message.send.max.retries': 3,
        })

    def send(self, topic: str, payload, key):
        payload = payload.encode('utf-8')

        self._producer.produce(
            topic=topic,
            key=key.encode('utf-8'),  #ключ
            value=payload,
            callback=self._delivery_report
        )
        self._producer.poll(0)

    def flush(self):
        """Сбрасывает буфер, ждёт подтверждения всех сообщений."""
        self._producer.flush()
        print("[Kafka] Буфер продюсера очищен.")

    @staticmethod
    def _delivery_report(err, msg):
        if err is not None:
            print(f"[Kafka ERROR] {err}")
        # else:
        #     print(f"[Kafka OK] Топик: {msg.topic()}, "
        #           f"партиция: {msg.partition()}, offset: {msg.offset()}")