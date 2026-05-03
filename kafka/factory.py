from confluent_kafka import Consumer


class KafkaConsumerFactory:
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
                                 fetch_min_bytes: int = 1024 * 30,
                                 fetch_max_wait_ms: int = 100,
                                 max_partition_fetch_bytes: int = 1024 * 1024,
                                 queued_max_messages_kbytes: int = 1024 * 1024,
                                 **overrides) -> Consumer:
        config = KafkaConsumerFactory.create_base_config(
            bootstrap_servers, group_id, client_id
        )
        config.update({
            'group.instance.id': group_instance_id,
            'fetch.min.bytes': fetch_min_bytes,
            'fetch.wait.max.ms': fetch_max_wait_ms,
            'max.partition.fetch.bytes': max_partition_fetch_bytes,
            'queued.max.messages.kbytes': queued_max_messages_kbytes,
        })
        config.update(overrides)
        return Consumer(config)