"""
Macro calendar and time filters for CFD Trader Assistant.
"""
import yaml
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MacroCalendar:
    """Handles macro economic events and time-based trading filters."""
    
    def __init__(self, config_path: str = "config/macro.yaml"):
        self.config_path = config_path
        self.events = []
        self.load_events()
    
    def load_events(self):
        """Load macro events from configuration file."""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"Macro config file not found: {self.config_path}")
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.events = config.get('important_events', [])
            logger.info(f"Loaded {len(self.events)} macro events")
            
        except Exception as e:
            logger.error(f"Error loading macro events: {e}")
            self.events = []
    
    def get_events_for_date(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Get all events scheduled for a specific date.
        
        Args:
            date: Date to check for events
            
        Returns:
            List of events for the given date
        """
        target_date = date.date()
        events_today = []
        
        for event in self.events:
            for schedule_str in event.get('schedule', []):
                try:
                    event_time = datetime.fromisoformat(schedule_str.replace('Z', '+00:00'))
                    if event_time.date() == target_date:
                        events_today.append({
                            'name': event['name'],
                            'time': event_time,
                            'impact': event.get('impact', 'medium')
                        })
                except ValueError as e:
                    logger.warning(f"Invalid date format in macro config: {schedule_str}")
        
        return events_today
    
    def get_events_in_window(
        self,
        start_time: datetime,
        end_time: datetime,
        impact_levels: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events within a time window.
        
        Args:
            start_time: Start of time window
            end_time: End of time window
            impact_levels: Filter by impact level (high, medium, low)
            
        Returns:
            List of events within the time window
        """
        if impact_levels is None:
            impact_levels = ['high', 'medium', 'low']
        
        events_in_window = []
        
        for event in self.events:
            for schedule_str in event.get('schedule', []):
                try:
                    event_time = datetime.fromisoformat(schedule_str.replace('Z', '+00:00'))
                    
                    if (start_time <= event_time <= end_time and 
                        event.get('impact', 'medium') in impact_levels):
                        events_in_window.append({
                            'name': event['name'],
                            'time': event_time,
                            'impact': event.get('impact', 'medium')
                        })
                except ValueError as e:
                    logger.warning(f"Invalid date format in macro config: {schedule_str}")
        
        return events_in_window
    
    def is_trading_allowed(
        self,
        current_time: datetime,
        no_trade_minutes_before: int = 30,
        no_trade_minutes_after: int = 30,
        impact_levels: List[str] = None
    ) -> Dict[str, Any]:
        """
        Check if trading is allowed at the current time based on macro events.
        
        Args:
            current_time: Current time to check
            no_trade_minutes_before: Minutes before event to avoid trading
            no_trade_minutes_after: Minutes after event to avoid trading
            impact_levels: Impact levels to consider for blocking
            
        Returns:
            Dictionary with 'allowed' boolean and 'reason' string
        """
        if impact_levels is None:
            impact_levels = ['high', 'medium']
        
        # Check for events in the no-trade window
        window_start = current_time - timedelta(minutes=no_trade_minutes_before)
        window_end = current_time + timedelta(minutes=no_trade_minutes_after)
        
        blocking_events = self.get_events_in_window(window_start, window_end, impact_levels)
        
        if blocking_events:
            # Find the closest event
            closest_event = min(blocking_events, key=lambda x: abs((x['time'] - current_time).total_seconds()))
            time_diff = (closest_event['time'] - current_time).total_seconds() / 60
            
            if time_diff < 0:
                reason = f"Trading blocked: {closest_event['name']} ended {abs(time_diff):.0f} minutes ago"
            else:
                reason = f"Trading blocked: {closest_event['name']} in {time_diff:.0f} minutes"
            
            return {
                'allowed': False,
                'reason': reason,
                'blocking_event': closest_event
            }
        
        return {
            'allowed': True,
            'reason': 'No blocking macro events',
            'blocking_event': None
        }
    
    def get_next_event(self, current_time: datetime, impact_levels: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the next upcoming macro event.
        
        Args:
            current_time: Current time
            impact_levels: Filter by impact level
            
        Returns:
            Next event or None if no upcoming events
        """
        if impact_levels is None:
            impact_levels = ['high', 'medium', 'low']
        
        upcoming_events = []
        
        for event in self.events:
            for schedule_str in event.get('schedule', []):
                try:
                    event_time = datetime.fromisoformat(schedule_str.replace('Z', '+00:00'))
                    
                    if (event_time > current_time and 
                        event.get('impact', 'medium') in impact_levels):
                        upcoming_events.append({
                            'name': event['name'],
                            'time': event_time,
                            'impact': event.get('impact', 'medium')
                        })
                except ValueError as e:
                    logger.warning(f"Invalid date format in macro config: {schedule_str}")
        
        if upcoming_events:
            return min(upcoming_events, key=lambda x: x['time'])
        
        return None
    
    def get_events_summary(self, days_ahead: int = 7) -> pd.DataFrame:
        """
        Get a summary of upcoming events.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            DataFrame with upcoming events
        """
        current_time = datetime.now(timezone.utc)
        end_time = current_time + timedelta(days=days_ahead)
        
        events = self.get_events_in_window(current_time, end_time)
        
        if not events:
            return pd.DataFrame()
        
        df = pd.DataFrame(events)
        df['time_until'] = df['time'] - current_time
        df['hours_until'] = df['time_until'].dt.total_seconds() / 3600
        df = df.sort_values('time')
        
        return df[['name', 'time', 'impact', 'hours_until']]


class TradingHoursFilter:
    """Handles trading hours and session filters."""
    
    def __init__(self, instruments_config: Dict[str, Any]):
        self.instruments_config = instruments_config
    
    def is_market_open(self, symbol: str, current_time: datetime = None) -> bool:
        """
        Check if market is open for a given symbol.
        
        Args:
            symbol: Trading symbol
            current_time: Time to check (defaults to now)
            
        Returns:
            True if market is open
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Find instrument config
        instrument = None
        for instr in self.instruments_config.get('instruments', []):
            if instr['symbol'] == symbol:
                instrument = instr
                break
        
        if not instrument:
            logger.warning(f"No trading hours config found for {symbol}")
            return True  # Default to allowing trading
        
        trading_hours = instrument.get('trading_hours')
        if not trading_hours:
            return True  # No restrictions
        
        try:
            # Convert current time to instrument timezone
            instrument_tz = trading_hours.get('timezone', 'UTC')
            if instrument_tz != 'UTC':
                # This is a simplified implementation
                # In production, you'd use pytz or zoneinfo for proper timezone handling
                logger.warning(f"Timezone conversion not fully implemented for {instrument_tz}")
            
            # Parse trading hours
            start_time = trading_hours.get('start', '00:00')
            end_time = trading_hours.get('end', '23:59')
            
            current_time_str = current_time.strftime('%H:%M')
            
            # Simple time comparison (assumes same day)
            return start_time <= current_time_str <= end_time
            
        except Exception as e:
            logger.error(f"Error checking trading hours for {symbol}: {e}")
            return True  # Default to allowing trading
    
    def get_market_status(self, symbol: str, current_time: datetime = None) -> Dict[str, Any]:
        """
        Get detailed market status for a symbol.
        
        Args:
            symbol: Trading symbol
            current_time: Time to check
            
        Returns:
            Dictionary with market status information
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        is_open = self.is_market_open(symbol, current_time)
        
        # Find instrument config
        instrument = None
        for instr in self.instruments_config.get('instruments', []):
            if instr['symbol'] == symbol:
                instrument = instr
                break
        
        trading_hours = instrument.get('trading_hours', {}) if instrument else {}
        
        return {
            'symbol': symbol,
            'is_open': is_open,
            'timezone': trading_hours.get('timezone', 'UTC'),
            'trading_hours': {
                'start': trading_hours.get('start', '00:00'),
                'end': trading_hours.get('end', '23:59')
            },
            'current_time': current_time,
            'status': 'OPEN' if is_open else 'CLOSED'
        }


class TimeFilter:
    """Combined time-based filters for trading decisions."""
    
    def __init__(self, macro_config_path: str = "config/macro.yaml", instruments_config: Dict[str, Any] = None):
        self.macro_calendar = MacroCalendar(macro_config_path)
        self.trading_hours = TradingHoursFilter(instruments_config or {})
    
    def can_trade(
        self,
        symbol: str,
        current_time: datetime = None,
        macro_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Check if trading is allowed based on all time filters.
        
        Args:
            symbol: Trading symbol
            current_time: Time to check
            macro_config: Macro filter configuration
            
        Returns:
            Dictionary with trading decision and reasons
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        if macro_config is None:
            macro_config = {
                'enabled': True,
                'no_trade_minutes_before': 30,
                'no_trade_minutes_after': 30
            }
        
        result = {
            'can_trade': True,
            'reasons': [],
            'blocking_factors': []
        }
        
        # Check macro events
        if macro_config.get('enabled', True):
            macro_check = self.macro_calendar.is_trading_allowed(
                current_time,
                macro_config.get('no_trade_minutes_before', 30),
                macro_config.get('no_trade_minutes_after', 30)
            )
            
            if not macro_check['allowed']:
                result['can_trade'] = False
                result['blocking_factors'].append('macro_event')
                result['reasons'].append(macro_check['reason'])
        
        # Check trading hours
        if not self.trading_hours.is_market_open(symbol, current_time):
            result['can_trade'] = False
            result['blocking_factors'].append('market_closed')
            result['reasons'].append(f"Market is closed for {symbol}")
        
        # Check if it's weekend (basic check)
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            result['can_trade'] = False
            result['blocking_factors'].append('weekend')
            result['reasons'].append("Trading not allowed on weekends")
        
        return result
    
    def get_trading_status_summary(self, symbols: List[str], current_time: datetime = None) -> pd.DataFrame:
        """
        Get trading status summary for multiple symbols.
        
        Args:
            symbols: List of symbols to check
            current_time: Time to check
            
        Returns:
            DataFrame with trading status for each symbol
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        status_data = []
        
        for symbol in symbols:
            can_trade = self.can_trade(symbol, current_time)
            market_status = self.trading_hours.get_market_status(symbol, current_time)
            
            status_data.append({
                'symbol': symbol,
                'can_trade': can_trade['can_trade'],
                'market_open': market_status['is_open'],
                'blocking_factors': ', '.join(can_trade['blocking_factors']),
                'reasons': '; '.join(can_trade['reasons']),
                'timezone': market_status['timezone']
            })
        
        return pd.DataFrame(status_data)
    
    def get_next_trading_opportunity(self, symbol: str, current_time: datetime = None) -> Optional[datetime]:
        """
        Get the next time when trading will be allowed for a symbol.
        
        Args:
            symbol: Trading symbol
            current_time: Current time
            
        Returns:
            Next trading opportunity or None
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Check next macro event
        next_event = self.macro_calendar.get_next_event(current_time)
        
        if next_event:
            # Trading will be allowed after the event + no_trade_minutes_after
            return next_event['time'] + timedelta(minutes=30)
        
        # If no macro events, check next market open
        # This is a simplified implementation
        # In production, you'd implement proper market hours logic
        
        return None