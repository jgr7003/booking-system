"""Reliable messaging shared by every module: Transactional Outbox, Inbox and RabbitMQ.

- A module that changes state calls `outbox.add_event` in the same transaction.
- The relay (`relay.run_relay`) publishes those events to RabbitMQ.
- Consumers (`consumer.consume`) receive them at least once and use `inbox` to stay idempotent.
- `broadcaster.EventBroadcaster` fans events out to the API's open connections (SSE).

It knows no module: exchanges, queues and routing keys come from each module's `Topology`.
"""
