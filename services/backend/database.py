"""
Database module for Backend API
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class Database:
    """Database operations for Backend API"""

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

    async def get_sites(self) -> List[Dict[str, Any]]:
        """Get all sites"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT DISTINCT location_site
                    FROM cards
                    WHERE location_site IS NOT NULL
                    ORDER BY location_site
                """)
                result = await session.execute(query)
                rows = result.fetchall()
                return [{"site_id": row[0], "name": row[0]} for row in rows]
        except Exception as e:
            logger.error(f"Error getting sites: {e}")
            return []

    async def get_cards(
        self,
        site_id: Optional[str] = None,
        family: Optional[str] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get cards with optional filters"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT card_serial, card_part, card_family, card_model,
                           location_site, slot_number, status,
                           installed_at, last_updated, created_at
                    FROM cards
                    WHERE 1=1
                """)
                params = {}
                
                if site_id:
                    query = text(str(query) + " AND location_site = :site_id")
                    params["site_id"] = site_id
                if family:
                    query = text(str(query) + " AND card_family = :family")
                    params["family"] = family
                if model:
                    query = text(str(query) + " AND card_model = :model")
                    params["model"] = model
                
                query = text(str(query) + " ORDER BY location_site, card_serial")
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                cards = []
                for row in rows:
                    cards.append({
                        "cardSerial": row[0],
                        "cardPart": row[1],
                        "cardFamily": row[2],
                        "cardModel": row[3],
                        "locationSite": row[4],
                        "slotNumber": row[5],
                        "status": row[6],
                        "installedAt": row[7].isoformat() if row[7] else None,
                        "lastUpdated": row[8].isoformat() if row[8] else None,
                        "createdAt": row[9].isoformat() if row[9] else None
                    })
                return cards
        except Exception as e:
            logger.error(f"Error getting cards: {e}")
            return []

    async def get_card(self, card_serial: str) -> Optional[Dict[str, Any]]:
        """Get a single card"""
        cards = await self.get_cards()
        return next((c for c in cards if c["cardSerial"] == card_serial), None)

    async def get_latest_measurements(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get latest measurements"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT DISTINCT ON (card_serial, measure_key)
                        time, card_serial, card_part, location_site,
                        measure_key, measure_name, measure_value,
                        measure_unit, measure_group, quality
                    FROM measurements
                    ORDER BY card_serial, measure_key, time DESC
                    LIMIT :limit OFFSET :offset
                """)
                result = await session.execute(query, {"limit": limit, "offset": offset})
                rows = result.fetchall()
                
                measurements = []
                for row in rows:
                    measurements.append({
                        "time": row[0].isoformat() if row[0] else None,
                        "cardSerial": row[1],
                        "cardPart": row[2],
                        "locationSite": row[3],
                        "measureKey": row[4],
                        "measureName": row[5],
                        "measureValue": row[6],
                        "measureUnit": row[7],
                        "measureGroup": row[8],
                        "quality": row[9]
                    })
                return measurements
        except Exception as e:
            logger.error(f"Error getting latest measurements: {e}")
            return []

    async def get_measurement_history(
        self,
        card_serial: str,
        measure_key: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: str = "1 hour"
    ) -> List[Dict[str, Any]]:
        """Get measurement history"""
        try:
            async with self.SessionLocal() as session:
                if interval:
                    # Use time_bucket for aggregation
                    query = text("""
                        SELECT 
                            time_bucket(:interval, time) AS bucket,
                            AVG(measure_value) AS avg_value,
                            MIN(measure_value) AS min_value,
                            MAX(measure_value) AS max_value
                        FROM measurements
                        WHERE card_serial = :card_serial
                    """)
                    params = {
                        "card_serial": card_serial,
                        "interval": interval
                    }
                    
                    if measure_key:
                        query = text(str(query) + " AND measure_key = :measure_key")
                        params["measure_key"] = measure_key
                    if start_time:
                        query = text(str(query) + " AND time >= :start_time")
                        params["start_time"] = start_time
                    if end_time:
                        query = text(str(query) + " AND time <= :end_time")
                        params["end_time"] = end_time
                    
                    query = text(str(query) + " GROUP BY bucket ORDER BY bucket")
                else:
                    # Raw data
                    query = text("""
                        SELECT time, measure_value
                        FROM measurements
                        WHERE card_serial = :card_serial
                    """)
                    params = {"card_serial": card_serial}
                    
                    if measure_key:
                        query = text(str(query) + " AND measure_key = :measure_key")
                        params["measure_key"] = measure_key
                    if start_time:
                        query = text(str(query) + " AND time >= :start_time")
                        params["start_time"] = start_time
                    if end_time:
                        query = text(str(query) + " AND time <= :end_time")
                        params["end_time"] = end_time
                    
                    query = text(str(query) + " ORDER BY time")
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                history = []
                for row in rows:
                    if interval:
                        history.append({
                            "time": row[0].isoformat() if row[0] else None,
                            "avgValue": float(row[1]) if row[1] else None,
                            "minValue": float(row[2]) if row[2] else None,
                            "maxValue": float(row[3]) if row[3] else None
                        })
                    else:
                        history.append({
                            "time": row[0].isoformat() if row[0] else None,
                            "value": float(row[1]) if row[1] else None
                        })
                return history
        except Exception as e:
            logger.error(f"Error getting measurement history: {e}")
            return []

    async def get_alarms(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        card_serial: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get alarms"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT 
                        a.alarm_id, a.alarm_type, a.severity, a.card_serial,
                        a.location_site, a.description, a.triggered_at,
                        a.cleared_at, a.status, a.acknowledged_at, a.acknowledged_by,
                        c.card_model,
                        CONCAT(a.location_site, '-[', a.card_serial, ']-', COALESCE(c.card_model, 'UNKNOWN')) as card_name
                    FROM alarms a
                    LEFT JOIN cards c ON a.card_serial = CAST(c.card_serial AS VARCHAR)
                    WHERE 1=1
                """)
                params = {}
                
                if status:
                    query = text(str(query) + " AND a.status = :status")
                    params["status"] = status
                if severity:
                    query = text(str(query) + " AND a.severity = :severity")
                    params["severity"] = severity
                if card_serial:
                    query = text(str(query) + " AND a.card_serial = :card_serial")
                    params["card_serial"] = card_serial
                if start_time:
                    query = text(str(query) + " AND a.triggered_at >= :start_time")
                    params["start_time"] = start_time
                
                query = text(str(query) + " ORDER BY a.triggered_at DESC LIMIT 1000")
                
                result = await session.execute(query, params)
                rows = result.fetchall()
                
                alarms = []
                for row in rows:
                    alarms.append({
                        "alarmId": row[0],
                        "alarmType": row[1],
                        "severity": row[2],
                        "cardSerial": row[3],
                        "locationSite": row[4],
                        "description": row[5],
                        "triggeredAt": row[6].isoformat() if row[6] else None,
                        "clearedAt": row[7].isoformat() if row[7] else None,
                        "status": row[8],
                        "acknowledgedAt": row[9].isoformat() if row[9] else None,
                        "acknowledgedBy": row[10],
                        "cardModel": row[11],
                        "cardName": row[12]
                    })
                return alarms
        except Exception as e:
            logger.error(f"Error getting alarms: {e}")
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

    async def get_alert_rules(self) -> List[Dict[str, Any]]:
        """Get alert rules"""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT rule_id, rule_name, measure_key, condition,
                           threshold_min, threshold_max, severity, enabled, hysteresis
                    FROM alert_rules
                    ORDER BY rule_id
                """)
                result = await session.execute(query)
                rows = result.fetchall()
                
                rules = []
                for row in rows:
                    rules.append({
                        "ruleId": row[0],
                        "ruleName": row[1],
                        "measureKey": row[2],
                        "condition": row[3],
                        "thresholdMin": row[4],
                        "thresholdMax": row[5],
                        "severity": row[6],
                        "enabled": row[7],
                        "hysteresis": row[8]
                    })
                return rules
        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []




