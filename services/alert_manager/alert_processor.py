"""
Alert Processor
Processa medições e aplica regras de alerta
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import pika

from database import Database

logger = logging.getLogger(__name__)


class AlertProcessor:
    """Process alerts based on rules"""

    def __init__(self, db: Database, rabbitmq_connection: Optional[pika.BlockingConnection]):
        """
        Initialize alert processor
        
        Args:
            db: Database instance
            rabbitmq_connection: RabbitMQ connection
        """
        self.db = db
        self.rabbitmq_connection = rabbitmq_connection
        self.active_alarms: Dict[str, Dict] = {}  # Track active alarms by key

    def _publish_message(self, queue: str, message: dict):
        """Publish message to RabbitMQ"""
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
                    delivery_mode=2,
                )
            )
            logger.debug(f"Published message to {queue}")
        except Exception as e:
            logger.error(f"Error publishing message: {e}")

    async def process_measurement(self, measurement: Dict[str, Any]):
        """
        Process a single measurement and check against rules
        
        Args:
            measurement: Measurement data dictionary
        """
        measure_key = measurement.get("measure_key")
        if not measure_key:
            return
        
        # Get rules for this measure_key
        rules = await self.db.get_alert_rules(enabled_only=True)
        relevant_rules = [r for r in rules if r["measure_key"] == measure_key]
        
        for rule in relevant_rules:
            await self._check_rule(rule, measurement)

    async def _check_rule(self, rule: Dict[str, Any], measurement: Dict[str, Any]):
        """
        Check a measurement against a specific rule
        
        Args:
            rule: Alert rule dictionary
            measurement: Measurement data dictionary
        """
        measure_value = measurement.get("measure_value")
        if measure_value is None:
            return
        
        card_serial = measurement.get("card_serial")
        alarm_key = f"{rule['rule_id']}_{card_serial}_{measurement.get('measure_key')}"
        
        condition = rule["condition"]
        threshold_min = rule.get("threshold_min")
        threshold_max = rule.get("threshold_max")
        hysteresis = rule.get("hysteresis", 0.5)
        severity = rule["severity"]
        
        should_trigger = False
        
        # Check condition
        if condition == "ABOVE":
            if threshold_max is not None:
                # Check if value is above threshold (with hysteresis)
                if measure_value > (threshold_max + hysteresis):
                    should_trigger = True
        elif condition == "BELOW":
            if threshold_min is not None:
                # Check if value is below threshold (with hysteresis)
                if measure_value < (threshold_min - hysteresis):
                    should_trigger = True
        elif condition == "RANGE":
            if threshold_min is not None and threshold_max is not None:
                # Check if value is outside range (with hysteresis)
                if measure_value < (threshold_min - hysteresis) or measure_value > (threshold_max + hysteresis):
                    should_trigger = True
        
        # Check if alarm is already active
        is_active = alarm_key in self.active_alarms
        
        if should_trigger and not is_active:
            # Trigger new alarm
            await self._trigger_alarm(rule, measurement, alarm_key)
        elif not should_trigger and is_active:
            # Clear existing alarm (with hysteresis check)
            await self._clear_alarm(rule, measurement, alarm_key, hysteresis)

    async def _trigger_alarm(
        self, 
        rule: Dict[str, Any], 
        measurement: Dict[str, Any],
        alarm_key: str
    ):
        """Trigger a new alarm"""
        card_serial = measurement.get("card_serial")
        measure_key = measurement.get("measure_key")
        measure_value = measurement.get("measure_value")
        measure_unit = measurement.get("measure_unit", "")
        location_site = measurement.get("location_site")
        
        alarm_id = f"ALARM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{card_serial}-{measure_key}"
        
        description = (
            f"{rule['rule_name']}: {measure_key} = {measure_value} {measure_unit} "
            f"(Card: {card_serial})"
        )
        
        alarm_data = {
            "alarm_id": alarm_id,
            "alarm_type": "THRESHOLD_EXCEEDED",
            "severity": rule["severity"],
            "card_serial": card_serial,
            "location_site": location_site,
            "description": description
        }
        
        # Store in database
        success = await self.db.create_alarm(alarm_data)
        if success:
            self.active_alarms[alarm_key] = alarm_data
            logger.warning(f"Alarm triggered: {alarm_id} - {description}")
            
            # Publish to RabbitMQ
            self._publish_message("alarms.triggered", {
                "event_type": "alarm_triggered",
                "timestamp": datetime.now().isoformat(),
                "data": alarm_data
            })

    async def _clear_alarm(
        self,
        rule: Dict[str, Any],
        measurement: Dict[str, Any],
        alarm_key: str,
        hysteresis: float
    ):
        """Clear an existing alarm (with hysteresis check)"""
        measure_value = measurement.get("measure_value")
        threshold_min = rule.get("threshold_min")
        threshold_max = rule.get("threshold_max")
        condition = rule["condition"]
        
        # Check if value is back to normal (with hysteresis)
        is_normal = False
        
        if condition == "ABOVE":
            if threshold_max is not None:
                is_normal = measure_value <= (threshold_max + hysteresis)
        elif condition == "BELOW":
            if threshold_min is not None:
                is_normal = measure_value >= (threshold_min - hysteresis)
        elif condition == "RANGE":
            if threshold_min is not None and threshold_max is not None:
                is_normal = (threshold_min - hysteresis) <= measure_value <= (threshold_max + hysteresis)
        
        if is_normal:
            alarm_data = self.active_alarms.get(alarm_key)
            if alarm_data:
                alarm_id = alarm_data["alarm_id"]
                success = await self.db.clear_alarm(alarm_id)
                if success:
                    del self.active_alarms[alarm_key]
                    logger.info(f"Alarm cleared: {alarm_id}")
                    
                    # Publish to RabbitMQ
                    self._publish_message("alarms.cleared", {
                        "event_type": "alarm_cleared",
                        "timestamp": datetime.now().isoformat(),
                        "data": {"alarm_id": alarm_id}
                    })

    async def check_degradation(self, rule: Dict[str, Any], measurement: Dict[str, Any]):
        """
        Check for degradation over time
        
        Args:
            rule: Alert rule dictionary
            measurement: Measurement data dictionary
        """
        if rule["condition"] != "DEGRADATION":
            return
        
        card_serial = measurement.get("card_serial")
        measure_key = measurement.get("measure_key")
        
        # Get history
        time_window = rule.get("time_window")
        hours = 1  # Default to 1 hour
        if time_window:
            # Parse interval (e.g., "1 hour")
            try:
                hours = int(time_window.split()[0])
            except:
                pass
        
        history = await self.db.get_measurement_history(card_serial, measure_key, hours)
        
        if len(history) < 2:
            return
        
        # Calculate average values
        current_avg = sum(h["value"] for h in history[-10:]) / min(10, len(history))
        previous_avg = sum(h["value"] for h in history[:10]) / min(10, len(history))
        
        threshold_min = rule.get("threshold_min")
        if threshold_min and (current_avg - previous_avg) < threshold_min:
            # Degradation detected
            alarm_key = f"{rule['rule_id']}_{card_serial}_{measure_key}_degradation"
            if alarm_key not in self.active_alarms:
                await self._trigger_alarm(rule, measurement, alarm_key)

    async def check_all_rules(self):
        """Check all rules against latest measurements"""
        logger.info("Checking all alert rules")
        
        # Get all enabled rules
        rules = await self.db.get_alert_rules(enabled_only=True)
        
        # Get latest measurements
        measurements = await self.db.get_latest_measurements()
        
        # Process each measurement
        for measurement in measurements:
            measure_key = measurement.get("measure_key")
            relevant_rules = [r for r in rules if r["measure_key"] == measure_key]
            
            for rule in relevant_rules:
                if rule["condition"] == "DEGRADATION":
                    await self.check_degradation(rule, measurement)
                else:
                    await self._check_rule(rule, measurement)
        
        logger.info(f"Completed checking {len(rules)} rules against {len(measurements)} measurements")




