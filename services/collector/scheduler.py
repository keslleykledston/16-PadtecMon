"""
Scheduler for data collection tasks
"""
import logging
from typing import Optional
import pika
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import json

from database import Database
from padtec_client import PadtecClient

logger = logging.getLogger(__name__)


class CollectorScheduler:
    """Scheduler for periodic data collection"""

    def __init__(
        self,
        db: Database,
        padtec_client: PadtecClient,
        rabbitmq_connection: Optional[pika.BlockingConnection],
        critical_interval: int = 30,
        normal_interval: int = 300
    ):
        """
        Initialize collector scheduler
        
        Args:
            db: Database instance
            padtec_client: Padtec API client
            rabbitmq_connection: RabbitMQ connection
            critical_interval: Interval for critical measurements (seconds)
            normal_interval: Interval for normal measurements (seconds)
        """
        self.db = db
        self.padtec_client = padtec_client
        self.rabbitmq_connection = rabbitmq_connection
        self.critical_interval = critical_interval
        self.normal_interval = normal_interval

    def _publish_message(self, queue: str, message: dict):
        """
        Publish message to RabbitMQ
        
        Args:
            queue: Queue name
            message: Message dictionary
        """
        if not self.rabbitmq_connection or self.rabbitmq_connection.is_closed:
            logger.warning("RabbitMQ connection not available")
            return
        
        try:
            channel = self.rabbitmq_connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            logger.debug(f"Published message to {queue}")
        except Exception as e:
            logger.error(f"Error publishing message: {e}")

    async def collect_cards(self):
        """Collect card inventory from Padtec API"""
        logger.info("Starting card collection")
        try:
            cards = await self.padtec_client.get_cards()
            logger.info(f"Fetched {len(cards)} cards from API")
            
            for card in cards:
                success = await self.db.upsert_card(card)
                if success:
                    logger.debug(f"Upserted card: {card.get('cardSerial')}")
            
            logger.info(f"Card collection completed: {len(cards)} cards processed")
        except Exception as e:
            logger.error(f"Error in card collection: {e}")

    async def collect_measurements_critical(self):
        """Collect critical measurements (Pump Power, OSNR)"""
        logger.info("Starting critical measurements collection")
        await self._collect_measurements(critical=True)

    async def collect_measurements_normal(self):
        """Collect normal measurements"""
        logger.info("Starting normal measurements collection")
        await self._collect_measurements(critical=False)

    async def _collect_measurements(self, critical: bool = False):
        """
        Collect measurements from Padtec API
        
        Args:
            critical: If True, collect only critical measurements
        """
        try:
            # Get all cards
            cards = await self.db.get_all_cards()
            if not cards:
                logger.warning("No cards found in database, fetching from API")
                await self.collect_cards()
                cards = await self.db.get_all_cards()
            
            critical_keys = ["PUMP_POWER", "OSNR", "OSC_POWER"]
            
            total_measurements = 0
            for card in cards:
                card_serial = card.get("cardSerial")
                if not card_serial:
                    continue
                
                try:
                    measurements = await self.padtec_client.get_measurements(
                        card_serial=card_serial
                    )
                    
                    for measurement in measurements:
                        measure_key = measurement.get("measureKey", "")
                        
                        # Filter by criticality if needed
                        if critical:
                            if not any(key in measure_key.upper() for key in critical_keys):
                                continue
                        
                        # Insert measurement
                        success = await self.db.insert_measurement(measurement)
                        if success:
                            total_measurements += 1
                            
                            # Publish to RabbitMQ
                            self._publish_message("measurements.collected", {
                                "event_type": "measurement_collected",
                                "timestamp": datetime.now().isoformat(),
                                "data": {
                                    "card_serial": card_serial,
                                    "measure_key": measure_key,
                                    "measure_value": measurement.get("measureValue"),
                                    "measure_unit": measurement.get("measureUnit"),
                                    "location_site": card.get("locationSite")
                                }
                            })
                    
                except Exception as e:
                    logger.error(f"Error collecting measurements for card {card_serial}: {e}")
                    continue
            
            logger.info(f"Measurements collection completed: {total_measurements} measurements processed")
        except Exception as e:
            logger.error(f"Error in measurements collection: {e}")

    async def collect_alarms(self):
        """Collect active alarms"""
        logger.info("Starting alarm collection")
        try:
            # Fetch active alarms from API
            api_alarms = await self.padtec_client.get_alarms(status="ACTIVE")
            logger.info(f"Fetched {len(api_alarms)} active alarms from API")
            
            # Get IDs of currently active alarms in DB
            db_active_ids = set(await self.db.get_active_alarm_ids())
            
            # Track IDs found in this collection
            current_ids = set()
            
            count = 0
            for alarm in api_alarms:
                # Generate ID to match database logic
                alarm_id = str(alarm.get("id") or alarm.get("alarmId") or alarm.get("alarmUid"))
                
                if not alarm_id or alarm_id == "None":
                    import hashlib
                    # Parse timestamp
                    triggered_at_str = (
                        alarm.get("alarmStartDate") or 
                        alarm.get("triggeredAt") or 
                        alarm.get("timestamp")
                    )
                    
                    if isinstance(triggered_at_str, str):
                        try:
                            triggered_at = datetime.strptime(triggered_at_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            triggered_at = datetime.now()
                    elif isinstance(triggered_at_str, (int, float)):
                        triggered_at = datetime.fromtimestamp(triggered_at_str)
                    else:
                        triggered_at = datetime.now()

                    alarm_type = str(alarm.get("alarmGroup") or alarm.get("type") or alarm.get("alarmType", "UNKNOWN"))
                    card_serial = str(alarm.get("cardSerial", ""))
                    
                    unique_str = f"{card_serial}_{alarm_type}_{triggered_at}"
                    alarm_id = hashlib.md5(unique_str.encode()).hexdigest()
                
                current_ids.add(alarm_id)
                
                # Pass ID explicitly to ensure consistency
                alarm['id'] = alarm_id
                
                if await self.db.upsert_alarm(alarm):
                    count += 1
            
            # Identify alarms that are no longer active
            cleared_ids = list(db_active_ids - current_ids)
            
            if cleared_ids:
                updated_count = await self.db.update_alarms_status(cleared_ids, "CLEARED")
                logger.info(f"Cleared {updated_count} alarms that are no longer active")
            
            logger.info(f"Alarm collection completed: {count} alarms upserted, {len(cleared_ids)} cleared")
        except Exception as e:
            logger.error(f"Error in alarm collection: {e}")

    async def collect_all(self):
        """Collect all data (cards, measurements, alarms)"""
        await self.collect_cards()
        await self.collect_alarms()
        await self.collect_measurements_critical()
        await self.collect_measurements_normal()

    async def setup_jobs(self, scheduler: AsyncIOScheduler):
        """
        Setup scheduled jobs
        
        Args:
            scheduler: APScheduler instance
        """
        # Collect cards daily at 00:01
        from apscheduler.triggers.cron import CronTrigger
        scheduler.add_job(
            self.collect_cards,
            CronTrigger(hour=0, minute=1),
            id='collect_cards',
            name='Collect Cards Inventory',
            replace_existing=True
        )
        
        # Collect alarms every 15 seconds
        scheduler.add_job(
            self.collect_alarms,
            'interval',
            seconds=15,
            id='collect_alarms',
            name='Collect Active Alarms',
            replace_existing=True
        )
        
        # Collect critical measurements every 30-60 seconds
        scheduler.add_job(
            self.collect_measurements_critical,
            'interval',
            seconds=self.critical_interval,
            id='collect_measurements_critical',
            name='Collect Critical Measurements',
            replace_existing=True
        )
        
        # Collect normal measurements every 5 minutes
        scheduler.add_job(
            self.collect_measurements_normal,
            'interval',
            seconds=self.normal_interval,
            id='collect_measurements_normal',
            name='Collect Normal Measurements',
            replace_existing=True
        )
        
        logger.info("Scheduled jobs configured")




