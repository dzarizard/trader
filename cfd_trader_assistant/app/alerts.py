"""
Alert system for CFD Trader Assistant.
Supports Telegram, Slack, and Email notifications.
"""
import os
import json
import smtplib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AlertMessage(BaseModel):
    """Alert message model."""
    title: str
    content: str
    priority: str = "normal"  # low, normal, high, critical
    timestamp: datetime
    symbol: str
    signal_type: str  # entry, exit, warning, info


class TelegramNotifier:
    """Telegram notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.bot_token = config.get('bot_token') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = config.get('chat_id') or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if self.enabled and not self.bot_token:
            logger.warning("Telegram enabled but no bot token provided")
            self.enabled = False
    
    def send_message(self, message: AlertMessage) -> bool:
        """
        Send message via Telegram.
        
        Args:
            message: Alert message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Format message for Telegram
            formatted_message = self._format_telegram_message(message)
            
            # Send message
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': formatted_message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram message sent for {message.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def _format_telegram_message(self, message: AlertMessage) -> str:
        """Format message for Telegram with HTML."""
        # Add emoji based on signal type
        emoji_map = {
            'entry': '🚀',
            'exit': '🏁',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        emoji = emoji_map.get(message.signal_type, '📊')
        
        # Format timestamp
        timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Create formatted message
        formatted = f"{emoji} <b>{message.title}</b>\n\n"
        formatted += f"<b>Symbol:</b> {message.symbol}\n"
        formatted += f"<b>Time:</b> {timestamp_str}\n"
        formatted += f"<b>Type:</b> {message.signal_type.upper()}\n\n"
        formatted += message.content
        
        return formatted


class SlackNotifier:
    """Slack notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.bot_token = config.get('bot_token') or os.getenv('SLACK_BOT_TOKEN')
        self.channel = config.get('channel') or os.getenv('SLACK_CHANNEL', '#trading-alerts')
        self.webhook_url = config.get('webhook_url')
        
        if self.enabled and not (self.bot_token or self.webhook_url):
            logger.warning("Slack enabled but no bot token or webhook URL provided")
            self.enabled = False
    
    def send_message(self, message: AlertMessage) -> bool:
        """
        Send message via Slack.
        
        Args:
            message: Alert message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Format message for Slack
            slack_message = self._format_slack_message(message)
            
            if self.webhook_url:
                # Use webhook
                response = requests.post(self.webhook_url, json=slack_message, timeout=10)
                response.raise_for_status()
            else:
                # Use bot API
                url = "https://slack.com/api/chat.postMessage"
                headers = {
                    'Authorization': f'Bearer {self.bot_token}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'channel': self.channel,
                    **slack_message
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                if not result.get('ok'):
                    raise Exception(f"Slack API error: {result.get('error')}")
            
            logger.info(f"Slack message sent for {message.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    def _format_slack_message(self, message: AlertMessage) -> Dict[str, Any]:
        """Format message for Slack."""
        # Add emoji based on signal type
        emoji_map = {
            'entry': ':rocket:',
            'exit': ':checkered_flag:',
            'warning': ':warning:',
            'info': ':information_source:'
        }
        
        emoji = emoji_map.get(message.signal_type, ':chart_with_upwards_trend:')
        
        # Format timestamp
        timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Create Slack message
        slack_message = {
            'text': f"{emoji} {message.title}",
            'blocks': [
                {
                    'type': 'header',
                    'text': {
                        'type': 'plain_text',
                        'text': f"{emoji} {message.title}"
                    }
                },
                {
                    'type': 'section',
                    'fields': [
                        {
                            'type': 'mrkdwn',
                            'text': f"*Symbol:* {message.symbol}"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Time:* {timestamp_str}"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Type:* {message.signal_type.upper()}"
                        },
                        {
                            'type': 'mrkdwn',
                            'text': f"*Priority:* {message.priority.upper()}"
                        }
                    ]
                },
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': message.content
                    }
                }
            ]
        }
        
        return slack_message


class EmailNotifier:
    """Email notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.smtp_server = config.get('smtp_server') or os.getenv('SMTP_SERVER')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username') or os.getenv('EMAIL_USER')
        self.password = config.get('password') or os.getenv('EMAIL_PASSWORD')
        self.to_address = config.get('to_address') or os.getenv('EMAIL_TO')
        
        if self.enabled and not all([self.smtp_server, self.username, self.password, self.to_address]):
            logger.warning("Email enabled but missing required configuration")
            self.enabled = False
    
    def send_message(self, message: AlertMessage) -> bool:
        """
        Send message via Email.
        
        Args:
            message: Alert message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = self.to_address
            msg['Subject'] = f"[CFD Trader] {message.title}"
            
            # Format email body
            body = self._format_email_message(message)
            msg.attach(MimeText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, self.to_address, text)
            server.quit()
            
            logger.info(f"Email sent for {message.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _format_email_message(self, message: AlertMessage) -> str:
        """Format message for email with HTML."""
        # Add emoji based on signal type
        emoji_map = {
            'entry': '🚀',
            'exit': '🏁',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        emoji = emoji_map.get(message.signal_type, '📊')
        
        # Format timestamp
        timestamp_str = message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Create HTML email
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
                .content {{ padding: 10px; }}
                .info {{ background-color: #e7f3ff; padding: 10px; border-left: 4px solid #2196F3; }}
                .warning {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; }}
                .success {{ background-color: #d4edda; padding: 10px; border-left: 4px solid #28a745; }}
                .danger {{ background-color: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{emoji} {message.title}</h2>
            </div>
            <div class="content">
                <p><strong>Symbol:</strong> {message.symbol}</p>
                <p><strong>Time:</strong> {timestamp_str}</p>
                <p><strong>Type:</strong> {message.signal_type.upper()}</p>
                <p><strong>Priority:</strong> {message.priority.upper()}</p>
            </div>
            <div class="content">
                {message.content.replace(chr(10), '<br>')}
            </div>
        </body>
        </html>
        """
        
        return html


class AlertManager:
    """Main alert management system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.telegram = TelegramNotifier(config.get('telegram', {}))
        self.slack = SlackNotifier(config.get('slack', {}))
        self.email = EmailNotifier(config.get('email', {}))
        
        # Rate limiting
        self.last_alert_times = {}
        self.min_alert_interval = 60  # Minimum 60 seconds between alerts for same symbol
    
    def send_signal_alert(self, signal, position_plan, instrument_config: Dict[str, Any]) -> bool:
        """
        Send signal entry alert.
        
        Args:
            signal: Trading signal
            position_plan: Position sizing plan
            instrument_config: Instrument configuration
            
        Returns:
            True if at least one alert was sent successfully
        """
        try:
            # Check rate limiting
            if self._is_rate_limited(signal.symbol):
                logger.warning(f"Rate limited for {signal.symbol}")
                return False
            
            # Create alert message
            message = self._create_signal_message(signal, position_plan, instrument_config)
            
            # Send via all enabled channels
            success = False
            if self.telegram.send_message(message):
                success = True
            if self.slack.send_message(message):
                success = True
            if self.email.send_message(message):
                success = True
            
            if success:
                self.last_alert_times[signal.symbol] = datetime.now()
                logger.info(f"Signal alert sent for {signal.symbol}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
            return False
    
    def send_exit_alert(self, signal, exit_reason: str, pnl: float = None) -> bool:
        """
        Send signal exit alert.
        
        Args:
            signal: Trading signal
            exit_reason: Reason for exit
            pnl: Profit/Loss amount
            
        Returns:
            True if at least one alert was sent successfully
        """
        try:
            # Create exit message
            message = self._create_exit_message(signal, exit_reason, pnl)
            
            # Send via all enabled channels
            success = False
            if self.telegram.send_message(message):
                success = True
            if self.slack.send_message(message):
                success = True
            if self.email.send_message(message):
                success = True
            
            if success:
                logger.info(f"Exit alert sent for {signal.symbol}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending exit alert: {e}")
            return False
    
    def send_warning_alert(self, title: str, content: str, symbol: str = None) -> bool:
        """
        Send warning alert.
        
        Args:
            title: Alert title
            content: Alert content
            symbol: Optional symbol
            
        Returns:
            True if at least one alert was sent successfully
        """
        try:
            message = AlertMessage(
                title=title,
                content=content,
                priority="high",
                timestamp=datetime.now(),
                symbol=symbol or "SYSTEM",
                signal_type="warning"
            )
            
            # Send via all enabled channels
            success = False
            if self.telegram.send_message(message):
                success = True
            if self.slack.send_message(message):
                success = True
            if self.email.send_message(message):
                success = True
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending warning alert: {e}")
            return False
    
    def _create_signal_message(self, signal, position_plan, instrument_config: Dict[str, Any]) -> AlertMessage:
        """Create signal entry message."""
        # Format entry alert content
        content = f"{signal.side} {signal.symbol} @ {signal.entry_price:.4f}\n"
        content += f"SL: {signal.stop_loss:.4f}  TP: {signal.take_profit:.4f}   RR: {signal.risk_reward_ratio:.1f}\n"
        content += f"Risk: ${position_plan.risk_amount:.2f} ({position_plan.risk_pct:.2f}% kapitału)  Size: {position_plan.size_units:.2f}\n"
        content += f"{signal.why}"
        
        return AlertMessage(
            title=f"New {signal.side} Signal",
            content=content,
            priority="high",
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            signal_type="entry"
        )
    
    def _create_exit_message(self, signal, exit_reason: str, pnl: float = None) -> AlertMessage:
        """Create signal exit message."""
        content = f"{signal.side} {signal.symbol} EXIT\n"
        content += f"Entry: {signal.entry_price:.4f}  Exit: {exit_reason}\n"
        
        if pnl is not None:
            pnl_emoji = "💰" if pnl > 0 else "💸"
            content += f"{pnl_emoji} P&L: ${pnl:.2f}\n"
        
        content += f"Reason: {exit_reason}"
        
        return AlertMessage(
            title=f"{signal.side} Signal Exit",
            content=content,
            priority="normal",
            timestamp=datetime.now(),
            symbol=signal.symbol,
            signal_type="exit"
        )
    
    def _is_rate_limited(self, symbol: str) -> bool:
        """Check if symbol is rate limited."""
        if symbol not in self.last_alert_times:
            return False
        
        last_alert = self.last_alert_times[symbol]
        time_since_last = (datetime.now() - last_alert).total_seconds()
        
        return time_since_last < self.min_alert_interval
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get alert system status."""
        return {
            'telegram': {
                'enabled': self.telegram.enabled,
                'configured': bool(self.telegram.bot_token and self.telegram.chat_id)
            },
            'slack': {
                'enabled': self.slack.enabled,
                'configured': bool(self.slack.bot_token or self.slack.webhook_url)
            },
            'email': {
                'enabled': self.email.enabled,
                'configured': bool(self.email.smtp_server and self.email.username and self.email.password)
            },
            'rate_limited_symbols': list(self.last_alert_times.keys())
        }