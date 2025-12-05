"""
Database module for Alert Manager
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class Database:
    """Database operations for Alert Manager"""

    def __init__(self, database_url: str):
        """Initialize database connection"""
        self.database_url = database_url
        if database_url.startswith("postgresql://"):
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            async_url = database_url
        
        self.engine = create_async_engine(async_url, echo=False)
        self.SessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self):
        """Initialize database connection"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
        logger.info("Database connection closed")

    async def get_alert_rules(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Get alert rules from database"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT rule_id, rule_name, measure_key, condition,
                           threshold_min, threshold_max, severity, enabled, hysteresis, time_window
                    FROM alert_rules
                    WHERE enabled = :enabled OR :enabled = FALSE
                    ORDER BY rule_id
                """)
                result = await session.execute(query, {"enabled": enabled_only})
                rows = result.fetchall()
                
                rules = []
                for row in rows:
                    rules.append({
                        "rule_id": row[0],
                        "rule_name": row[1],
                        "measure_key": row[2],
                        "condition": row[3],
                        "threshold_min": row[4],
                        "threshold_max": row[5],
                        "severity": row[6],
                        "enabled": row[7],
                        "hysteresis": row[8],
                        "time_window": str(row[9]) if row[9] else None
                    })
                return rules
        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []

    async def get_latest_measurements(
        self, 
        measure_key: Optional[str] = None,
        card_serial: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get latest measurements"""
        try:
            async with self.SessionLocal() as session:
                if measure_key and card_serial:
                    query = text("""
                        SELECT DISTINCT ON (card_serial, measure_key)
                            time, card_serial, card_part, location_site,
                            measure_key, measure_name, measure_value,
                            measure_unit, measure_group, quality
                        FROM measurements
                        WHERE measure_key = :measure_key AND card_serial = :card_serial
                        ORDER BY card_serial, measure_key, time DESC
                    """)
                    result = await session.execute(query, {
                        "measure_key": measure_key,
                        "card_serial": card_serial
                    })
                elif measure_key:
                    query = text("""
                        SELECT DISTINCT ON (card_serial, measure_key)
                            time, card_serial, card_part, location_site,
                            measure_key, measure_name, measure_value,
                            measure_unit, measure_group, quality
                        FROM measurements
                        WHERE measure_key = :measure_key
                        ORDER BY card_serial, measure_key, time DESC
                    """)
                    result = await session.execute(query, {"measure_key": measure_key})
                else:
                    query = text("""
                        SELECT DISTINCT ON (card_serial, measure_key)
                            time, card_serial, card_part, location_site,
                            measure_key, measure_name, measure_value,
                            measure_unit, measure_group, quality
                        FROM measurements
                        ORDER BY card_serial, measure_key, time DESC
                    """)
                    result = await session.execute(query)
                
                rows = result.fetchall()
                measurements = []
                for row in rows:
                    measurements.append({
                        "time": row[0].isoformat() if row[0] else None,
                        "card_serial": row[1],
                        "card_part": row[2],
                        "location_site": row[3],
                        "measure_key": row[4],
                        "measure_name": row[5],
                        "measure_value": row[6],
                        "measure_unit": row[7],
                        "measure_group": row[8],
                        "quality": row[9]
                    })
                return measurements
        except Exception as e:
            logger.error(f"Error getting latest measurements: {e}")
            return []

    async def get_measurement_history(
        self,
        card_serial: str,
        measure_key: str,
        hours: int = 1
    ) -> List[Dict[str, Any]]:
        """Get measurement history for degradation detection"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT time, measure_value
                    FROM measurements
                    WHERE card_serial = :card_serial
                      AND measure_key = :measure_key
                      AND time > NOW() - INTERVAL ':hours hours'
                    ORDER BY time ASC
                """)
                result = await session.execute(query, {
                    "card_serial": card_serial,
                    "measure_key": measure_key,
                    "hours": hours
                })
                rows = result.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        "time": row[0].isoformat() if row[0] else None,
                        "value": row[1]
                    })
                return history
        except Exception as e:
            logger.error(f"Error getting measurement history: {e}")
            return []

    async def create_alarm(self, alarm_data: Dict[str, Any]) -> bool:
        """Create a new alarm"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    INSERT INTO alarms (
                        alarm_id, alarm_type, severity, card_serial,
                        location_site, description, triggered_at, status
                    ) VALUES (
                        :alarm_id, :alarm_type, :severity, :card_serial,
                        :location_site, :description, :triggered_at, 'ACTIVE'
                    )
                    ON CONFLICT (alarm_id) DO UPDATE SET
                        status = 'ACTIVE',
                        triggered_at = EXCLUDED.triggered_at,
                        cleared_at = NULL
                """)
                
                await session.execute(query, {
                    "alarm_id": alarm_data["alarm_id"],
                    "alarm_type": alarm_data.get("alarm_type", "THRESHOLD_EXCEEDED"),
                    "severity": alarm_data["severity"],
                    "card_serial": alarm_data["card_serial"],
                    "location_site": alarm_data.get("location_site"),
                    "description": alarm_data["description"],
                    "triggered_at": datetime.now()
                })
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating alarm: {e}")
            return False

    async def get_active_alarms(self) -> List[Dict[str, Any]]:
        """Get active alarms"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT alarm_id, alarm_type, severity, card_serial,
                           location_site, description, triggered_at, status
                    FROM alarms
                    WHERE status = 'ACTIVE'
                    ORDER BY triggered_at DESC
                """)
                result = await session.execute(query)
                rows = result.fetchall()
                
                alarms = []
                for row in rows:
                    alarms.append({
                        "alarm_id": row[0],
                        "alarm_type": row[1],
                        "severity": row[2],
                        "card_serial": row[3],
                        "location_site": row[4],
                        "description": row[5],
                        "triggered_at": row[6].isoformat() if row[6] else None,
                        "status": row[7]
                    })
                return alarms
        except Exception as e:
            logger.error(f"Error getting active alarms: {e}")
            return []

    async def acknowledge_alarm(self, alarm_id: str) -> bool:
        """Acknowledge an alarm"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    UPDATE alarms
                    SET status = 'ACKNOWLEDGED',
                        acknowledged_at = NOW()
                    WHERE alarm_id = :alarm_id
                """)
                result = await session.execute(query, {"alarm_id": alarm_id})
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error acknowledging alarm: {e}")
            return False

    async def clear_alarm(self, alarm_id: str) -> bool:
        """Clear an alarm"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    UPDATE alarms
                    SET status = 'CLEARED',
                        cleared_at = NOW()
                    WHERE alarm_id = :alarm_id
                """)
                result = await session.execute(query, {"alarm_id": alarm_id})
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error clearing alarm: {e}")
            return False




