"""
RabbitMQ Consumer for Alert Manager
Consome mensagens de medições coletadas
"""
import logging
import json
import threading
from typing import Optional
import pika

from alert_processor import AlertProcessor

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Consumer for RabbitMQ messages"""

    def __init__(
        self,
        connection: pika.BlockingConnection,
        alert_processor: AlertProcessor
    ):
        """
        Initialize RabbitMQ consumer
        
        Args:
            connection: RabbitMQ connection
            alert_processor: Alert processor instance
        """
        self.connection = connection
        self.alert_processor = alert_processor
        self.channel = None
        self.consuming = False
        self.thread = None

    def _on_message(self, channel, method, properties, body):
        """Handle incoming message"""
        try:
            message = json.loads(body)
            event_type = message.get("event_type")
            data = message.get("data", {})
            
            if event_type == "measurement_collected":
                # Process measurement
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.alert_processor.process_measurement(data)
                )
                loop.close()
            
            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Reject message and requeue
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self):
        """Start consuming messages"""
        try:
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='measurements.collected', durable=True)
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue='measurements.collected',
                on_message_callback=self._on_message
            )
            
            self.consuming = True
            
            # Start consuming in a separate thread
            self.thread = threading.Thread(target=self._consume, daemon=True)
            self.thread.start()
            
            logger.info("Started consuming messages from RabbitMQ")
        except Exception as e:
            logger.error(f"Error starting consumer: {e}")

    def _consume(self):
        """Consume messages (runs in thread)"""
        try:
            while self.consuming:
                self.connection.process_data_events(time_limit=1)
        except Exception as e:
            logger.error(f"Error in consumer thread: {e}")

    def stop_consuming(self):
        """Stop consuming messages"""
        self.consuming = False
        if self.channel:
            try:
                self.channel.stop_consuming()
            except:
                pass
        logger.info("Stopped consuming messages from RabbitMQ")




