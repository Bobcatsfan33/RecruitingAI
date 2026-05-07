"""Event publisher + consumer.

Two destinations:
1. ClickHouse `interaction_events` — durable analytical store.
2. Redis Streams — low-latency cross-service fanout (one stream per agent).

Every event lands in both. Failures in either are caught and logged; the
calling agent never crashes due to an event-publishing error.
"""

from wfi_events.publisher import EventPublisher, NullEventPublisher
from wfi_events.consumer import RedisStreamConsumer

__all__ = ["EventPublisher", "NullEventPublisher", "RedisStreamConsumer"]
