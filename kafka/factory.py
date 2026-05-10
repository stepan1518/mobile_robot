from confluent_kafka import Consumer

from kafka.producer import KafkaProducerService


class KafkaAbstractFactory:
    """Фабрика для создания преднастроенных Consumer'ов."""

    @staticmethod
    def create_base_config(bootstrap_servers: str,
                           group_id: str = 'robot-server-group',
                           client_id: str = 'robot-server-consumer') -> dict:
        return {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'client.id': client_id,
            'enable.auto.commit': False,
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000,
            'auto.offset.reset': 'latest',
        }

    @staticmethod
    def create_realtime_consumer(bootstrap_servers: str,
                                 group_id: str = 'robot-server-group',
                                 client_id: str = 'robot-server-consumer',
                                 group_instance_id: str = 'static-consumer-1',
                                 fetch_min_bytes: int = 1048576,
                                 fetch_max_wait_ms: int = 50,
                                 max_partition_fetch_bytes: int = 10485760,
                                 queued_max_messages_kbytes: int = 1024 * 1024,
                                 fetch_max_bytes: int = 52428800,
                                 receive_buffer_bytes: int = 1048576,
                                 session_timeout_ms: int = 30000,
                                 heartbeat_interval_ms: int = 10000,
                                 max_poll_interval_ms: int = 300000) -> Consumer:
        config = KafkaAbstractFactory.create_base_config(
            bootstrap_servers, group_id, client_id
        )
        config.update({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'client.id': client_id,
            'group.instance.id': group_instance_id,
            'enable.auto.commit': False,
            'auto.offset.reset': 'latest',
            'fetch.min.bytes': fetch_min_bytes,
            'fetch.wait.max.ms': fetch_max_wait_ms,
            'max.partition.fetch.bytes': max_partition_fetch_bytes,
            'queued.max.messages.kbytes': queued_max_messages_kbytes,
            'fetch.max.bytes': fetch_max_bytes,
            'socket.receive.buffer.bytes': receive_buffer_bytes,
            'session.timeout.ms': session_timeout_ms,
            'heartbeat.interval.ms': heartbeat_interval_ms,
            'max.poll.interval.ms': max_poll_interval_ms,
        })
        return Consumer(config)

    @staticmethod
    def create_producer(bootstrap_servers: str, client_id: str) -> KafkaProducerService:
        return KafkaProducerService(bootstrap_servers, client_id)