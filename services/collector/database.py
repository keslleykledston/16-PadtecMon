"""
Database module for TimescaleDB operations
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class Database:
    """Database operations for TimescaleDB"""

    def __init__(self, database_url: str):
        """
        Initialize database connection
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        # Convert postgresql:// to postgresql+asyncpg:// for async
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
                # Test connection
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
        logger.info("Database connection closed")

    async def upsert_card(self, card_data: Dict[str, Any]) -> bool:
        """
        Insert or update card information
        
        Args:
            card_data: Card data dictionary
            
        Returns:
            True if successful
        """
        try:
            # Cast serial to string as it might be an integer from API
            card_serial = str(card_data.get("cardSerial"))
            
            async with self.SessionLocal() as session:
                query = text("""
                    INSERT INTO cards (
                        card_serial, card_part, card_family, card_model,
                        location_site, slot_number, status, installed_at, last_updated
                    ) VALUES (
                        :card_serial, :card_part, :card_family, :card_model,
                        :location_site, :slot_number, :status, :installed_at, :last_updated
                    )
                    ON CONFLICT (card_serial) DO UPDATE SET
                        card_part = EXCLUDED.card_part,
                        card_family = EXCLUDED.card_family,
                        card_model = EXCLUDED.card_model,
                        location_site = EXCLUDED.location_site,
                        slot_number = EXCLUDED.slot_number,
                        status = EXCLUDED.status,
                        last_updated = EXCLUDED.last_updated
                """)
                
                # Convert timestamps
                installed_at = None
                if card_data.get("installedAt"):
                    installed_at = datetime.fromtimestamp(card_data["installedAt"])
                
                last_updated = datetime.fromtimestamp(
                    card_data.get("lastUpdated", datetime.now().timestamp())
                )
                
                params = {
                    "card_serial": card_serial,
                    "card_part": str(card_data.get("cardPart", "")),
                    "card_family": str(card_data.get("cardFamily", "")),
                    "card_model": str(card_data.get("cardModel", "")),
                    "location_site": str(card_data.get("locationSite", "")),
                    "slot_number": card_data.get("slotNumber"),
                    "status": str(card_data.get("status", "UNKNOWN")),
                    "installed_at": installed_at,
                    "last_updated": last_updated
                }
                
                # logger.info(f"Upserting card {card_serial}: {params}")
                
                result = await session.execute(query, params)
                await session.commit()
                # logger.info(f"Card {card_serial} upserted. Rowcount: {result.rowcount}")
                return True
        except Exception as e:
            logger.error(f"Error upserting card {card_data.get('cardSerial')}: {e}")
            return False

    async def insert_measurement(self, measurement_data: Dict[str, Any]) -> bool:
        """
        Insert measurement data
        
        Args:
            measurement_data: Measurement data dictionary
            
        Returns:
            True if successful
        """
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    INSERT INTO measurements (
                        time, card_serial, card_part, location_site,
                        measure_key, measure_name, measure_value,
                        measure_unit, measure_group, quality
                    ) VALUES (
                        :time, :card_serial, :card_part, :location_site,
                        :measure_key, :measure_name, :measure_value,
                        :measure_unit, :measure_group, :quality
                    )
                    ON CONFLICT (time, card_serial, measure_key) DO UPDATE SET
                        measure_value = EXCLUDED.measure_value,
                        measure_unit = EXCLUDED.measure_unit,
                        measure_group = EXCLUDED.measure_group,
                        quality = EXCLUDED.quality
                """)
                
                # Convert timestamp
                timestamp = datetime.fromtimestamp(
                    measurement_data.get("timestamp") or 
                    measurement_data.get("updatedAt") or 
                    datetime.now().timestamp()
                )
                
                await session.execute(query, {
                    "time": timestamp,
                    "card_serial": measurement_data.get("cardSerial"),
                    "card_part": measurement_data.get("cardPart"),
                    "location_site": measurement_data.get("locationSite"),
                    "measure_key": measurement_data.get("measureKey"),
                    "measure_name": measurement_data.get("measureName"),
                    "measure_value": measurement_data.get("measureValue"),
                    "measure_unit": measurement_data.get("measureUnit"),
                    "measure_group": measurement_data.get("measureGroup"),
                    "quality": measurement_data.get("quality", "GOOD")
                })
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error inserting measurement: {e}")
            return False

    async def insert_measurements_batch(self, measurements: List[Dict[str, Any]]) -> int:
        """
        Insert multiple measurements in batch
        
        Args:
            measurements: List of measurement dictionaries
            
        Returns:
            Number of successfully inserted measurements
        """
        count = 0
        for measurement in measurements:
            if await self.insert_measurement(measurement):
                count += 1
        return count

    async def get_all_cards(self) -> List[Dict[str, Any]]:
        """
        Get all cards from database
        
        Returns:
            List of card dictionaries
        """
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT 
                        card_serial, card_part, card_family, card_model,
                        location_site, slot_number, status, 
                        installed_at, last_updated, created_at
                    FROM cards
                    ORDER BY location_site, card_serial
                """)
                result = await session.execute(query)
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
                        "installedAt": row[7].timestamp() if row[7] else None,
                        "lastUpdated": row[8].timestamp() if row[8] else None,
                        "createdAt": row[9].timestamp() if row[9] else None
                    })
                return cards
        except Exception as e:
            logger.error(f"Error getting cards: {e}")
            return []

    async def get_system_config(self) -> Dict[str, str]:
        """Fetch system configuration key/value pairs."""
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    SELECT config_key, config_value
                    FROM system_config
                """)
                result = await session.execute(query)
                rows = result.fetchall()
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Error fetching system configuration: {e}")
            return {}

    async def upsert_alarm(self, alarm_data: Dict[str, Any]) -> bool:
        """
        Insert or update alarm
        
        Args:
            alarm_data: Alarm data dictionary
            
        Returns:
            True if successful
        """
        try:
            async with self.SessionLocal() as session:
                query = text("""
                    INSERT INTO alarms (
                        alarm_id, alarm_type, severity, card_serial,
                        location_site, description, triggered_at,
                        status
                    ) VALUES (
                        :alarm_id, :alarm_type, :severity, :card_serial,
                        :location_site, :description, :triggered_at,
                        :status
                    )
                    ON CONFLICT (alarm_id) DO UPDATE SET
                        severity = EXCLUDED.severity,
                        status = EXCLUDED.status,
                        description = EXCLUDED.description
                """)
                
                # Convert timestamp
                # API returns "2025-11-13 15:46:15"
                triggered_at_str = (
                    alarm_data.get("alarmStartDate") or 
                    alarm_data.get("triggeredAt") or 
                    alarm_data.get("timestamp")
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
                
                params = {
                    "alarm_id": str(alarm_data.get("id") or alarm_data.get("alarmId") or alarm_data.get("alarmUid")),
                    "alarm_type": str(alarm_data.get("alarmGroup") or alarm_data.get("type") or alarm_data.get("alarmType", "UNKNOWN")),
                    "severity": str(alarm_data.get("alarmSeverity") or alarm_data.get("severity", "UNKNOWN")),
                    "card_serial": str(alarm_data.get("cardSerial", "")),
                    "location_site": str(alarm_data.get("locationSite", "")),
                    "description": str(alarm_data.get("alarmName") or alarm_data.get("description", "")),
                    "triggered_at": triggered_at,
                    "status": str(alarm_data.get("status", "ACTIVE"))
                }
                
                if not params["alarm_id"] or params["alarm_id"] == "None":
                    # Generate ID if missing (fallback)
                    import hashlib
                    unique_str = f"{params['card_serial']}_{params['alarm_type']}_{params['triggered_at']}"
                    params["alarm_id"] = hashlib.md5(unique_str.encode()).hexdigest()

                await session.execute(query, params)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Error upserting alarm: {e}")
            return False

    async def get_active_alarm_ids(self) -> List[str]:
        """Get IDs of all active alarms"""
        try:
            async with self.SessionLocal() as session:
                query = text("SELECT alarm_id FROM alarms WHERE status = 'ACTIVE'")
                result = await session.execute(query)
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting active alarm IDs: {e}")
            return []

    async def update_alarms_status(self, alarm_ids: List[str], status: str) -> int:
        """
        Update status for multiple alarms
        
        Args:
            alarm_ids: List of alarm IDs
            status: New status
            
        Returns:
            Number of updated rows
        """
        if not alarm_ids:
            return 0
            
        try:
            async with self.SessionLocal() as session:
                # Use ANY for array comparison with explicit cast
                query = text("""
                    UPDATE alarms 
                    SET status = CAST(:status AS VARCHAR), 
                        cleared_at = CASE WHEN CAST(:status AS VARCHAR) = 'CLEARED' THEN NOW() ELSE cleared_at END
                    WHERE alarm_id = ANY(CAST(:alarm_ids AS VARCHAR[]))
                """)
                result = await session.execute(query, {
                    "status": status,
                    "alarm_ids": alarm_ids
                })
                await session.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"Error updating alarms status: {e}")
            return 0

