"""
Notification Handler
Manages sending notifications through multiple channels
"""
import logging
from typing import Optional
import aiohttp
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class NotificationHandler:
    """Handle notifications through multiple channels"""

    def __init__(self, settings):
        """Initialize notification handler"""
        self.settings = settings
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from
        self.telegram_bot_token = settings.telegram_bot_token
        self.telegram_chat_id = settings.telegram_chat_id

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None
    ) -> bool:
        """
        Send email notification
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            html: Optional HTML body
            
        Returns:
            True if successful
        """
        if not self.smtp_server:
            logger.warning("SMTP server not configured")
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.smtp_from or self.smtp_user
            message["To"] = to
            message["Subject"] = subject
            
            # Add plain text part
            message.attach(MIMEText(body, "plain"))
            
            # Add HTML part if provided
            if html:
                message.attach(MIMEText(html, "html"))
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True
            )
            
            logger.info(f"Email sent to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_telegram(self, message: str) -> bool:
        """
        Send Telegram notification
        
        Args:
            message: Message text
            
        Returns:
            True if successful
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Telegram message sent")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Telegram API error: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    async def send_webhook(self, url: str, payload: dict) -> bool:
        """
        Send webhook notification
        
        Args:
            url: Webhook URL
            payload: Payload data
            
        Returns:
            True if successful
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status in [200, 201, 204]:
                        logger.info(f"Webhook sent to {url}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Webhook error: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False

    async def send_notification(
        self,
        alarm_data: dict,
        channels: list = None
    ):
        """
        Send notification for an alarm
        
        Args:
            alarm_data: Alarm data dictionary
            channels: List of channels to use (default: based on severity)
        """
        severity = alarm_data.get("severity", "MINOR")
        description = alarm_data.get("description", "Alarm triggered")
        card_serial = alarm_data.get("card_serial", "Unknown")
        location_site = alarm_data.get("location_site", "Unknown")
        
        # Determine channels based on severity if not specified
        if channels is None:
            if severity == "CRITICAL":
                channels = ["email", "telegram", "webhook"]
            elif severity == "MAJOR":
                channels = ["email", "telegram"]
            else:
                channels = ["email"]
        
        # Format message
        subject = f"[{severity}] Padtec Alarm: {description}"
        body = f"""
Padtec Monitoring System - Alarm Notification

Severity: {severity}
Description: {description}
Card Serial: {card_serial}
Location Site: {location_site}
Time: {alarm_data.get('triggered_at', 'Unknown')}

Please check the dashboard for more details.
        """.strip()
        
        html_body = f"""
        <html>
        <body>
        <h2>Padtec Monitoring System - Alarm Notification</h2>
        <p><strong>Severity:</strong> {severity}</p>
        <p><strong>Description:</strong> {description}</p>
        <p><strong>Card Serial:</strong> {card_serial}</p>
        <p><strong>Location Site:</strong> {location_site}</p>
        <p><strong>Time:</strong> {alarm_data.get('triggered_at', 'Unknown')}</p>
        <p>Please check the dashboard for more details.</p>
        </body>
        </html>
        """
        
        # Send through configured channels
        if "email" in channels and self.smtp_from:
            # Send to configured email (you can extend this to use alarm-specific emails)
            await self.send_email(
                to=self.smtp_from,  # Default recipient
                subject=subject,
                body=body,
                html=html_body
            )
        
        if "telegram" in channels:
            telegram_message = f"""
<b>{severity} Alarm</b>
{description}
Card: {card_serial}
Site: {location_site}
            """.strip()
            await self.send_telegram(telegram_message)
        
        if "webhook" in channels:
            # Webhook URL should be configured separately
            # For now, skip if not configured
            pass




