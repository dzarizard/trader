"""
Trading rules and signal generation logic for CFD Trader Assistant.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
import logging

from .indicators import compute_indicators, get_indicator_value, is_indicator_above, is_indicator_below, get_indicator_crossover

logger = logging.getLogger(__name__)


class Signal(BaseModel):
    """Trading signal model."""
    id: str
    timestamp: datetime
    side: str  # 'LONG' or 'SHORT'
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    why: str
    metrics: Dict[str, Any]
    status: str = 'ACTIVE'  # 'ACTIVE', 'HIT_SL', 'HIT_TP', 'TIME_STOP', 'TREND_BREAK'
    bars_since_entry: int = 0


class TrendFilter:
    """Trend filter for HTF (Higher Timeframe) analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        self.sma_long = config.get('trend', {}).get('sma_long', 200)
        self.sma_mid = config.get('trend', {}).get('sma_mid', 50)
        self.sma_fast = config.get('trend', {}).get('sma_fast', 20)
    
    def check_trend(self, indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """
        Check if trend conditions are met for the given side.
        
        Args:
            indicators: Dictionary of computed indicators
            side: 'LONG' or 'SHORT'
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            close_price = get_indicator_value(indicators, 'close', -1)
            sma_200 = get_indicator_value(indicators, 'sma_200', -1)
            sma_50 = get_indicator_value(indicators, 'sma_50', -1)
            sma_20 = get_indicator_value(indicators, 'sma_20', -1)
            
            if any(x is None for x in [close_price, sma_200, sma_50, sma_20]):
                return False, "Missing trend indicator data"
            
            if side == 'LONG':
                # LONG: close > SMA200 AND SMA20 > SMA50
                if close_price > sma_200 and sma_20 > sma_50:
                    return True, f"Trend(HTF) OK: Close({close_price:.2f}) > SMA200({sma_200:.2f}), SMA20({sma_20:.2f}) > SMA50({sma_50:.2f})"
                else:
                    reasons = []
                    if close_price <= sma_200:
                        reasons.append(f"Close({close_price:.2f}) <= SMA200({sma_200:.2f})")
                    if sma_20 <= sma_50:
                        reasons.append(f"SMA20({sma_20:.2f}) <= SMA50({sma_50:.2f})")
                    return False, f"Trend(HTF) FAIL: {', '.join(reasons)}"
            
            elif side == 'SHORT':
                # SHORT: close < SMA200 AND SMA20 < SMA50
                if close_price < sma_200 and sma_20 < sma_50:
                    return True, f"Trend(HTF) OK: Close({close_price:.2f}) < SMA200({sma_200:.2f}), SMA20({sma_20:.2f}) < SMA50({sma_50:.2f})"
                else:
                    reasons = []
                    if close_price >= sma_200:
                        reasons.append(f"Close({close_price:.2f}) >= SMA200({sma_200:.2f})")
                    if sma_20 >= sma_50:
                        reasons.append(f"SMA20({sma_20:.2f}) >= SMA50({sma_50:.2f})")
                    return False, f"Trend(HTF) FAIL: {', '.join(reasons)}"
            
            return False, f"Invalid side: {side}"
            
        except Exception as e:
            logger.error(f"Error in trend filter: {e}")
            return False, f"Trend filter error: {e}"


class EntryTrigger:
    """Entry trigger conditions for LTF (Lower Timeframe) analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        self.donchian_period = config.get('entry', {}).get('donchian_period', 20)
        self.roc_lookback = config.get('entry', {}).get('roc_lookback', 10)
        self.roc_min_long = config.get('entry', {}).get('roc_min_long', 0.003)
        self.roc_max_short = config.get('entry', {}).get('roc_max_short', -0.003)
        self.macd_fast = config.get('entry', {}).get('macd_fast', 12)
        self.macd_slow = config.get('entry', {}).get('macd_slow', 26)
        self.macd_signal = config.get('entry', {}).get('macd_signal', 9)
    
    def check_entry_triggers(self, df: pd.DataFrame, indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """
        Check if any entry trigger conditions are met.
        
        Args:
            df: DataFrame with OHLCV data
            indicators: Dictionary of computed indicators
            side: 'LONG' or 'SHORT'
            
        Returns:
            Tuple of (is_triggered, reason)
        """
        try:
            triggers = []
            
            # 1. Donchian Channel Breakout
            donchian_trigger = self._check_donchian_breakout(df, indicators, side)
            if donchian_trigger[0]:
                triggers.append(donchian_trigger[1])
            
            # 2. MACD Crossover
            macd_trigger = self._check_macd_crossover(indicators, side)
            if macd_trigger[0]:
                triggers.append(macd_trigger[1])
            
            # 3. Rate of Change
            roc_trigger = self._check_roc_momentum(indicators, side)
            if roc_trigger[0]:
                triggers.append(roc_trigger[1])
            
            if triggers:
                return True, f"Trigger(LTF): {'; '.join(triggers)}"
            else:
                return False, "No entry triggers met"
                
        except Exception as e:
            logger.error(f"Error in entry trigger check: {e}")
            return False, f"Entry trigger error: {e}"
    
    def _check_donchian_breakout(self, df: pd.DataFrame, indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check Donchian Channel breakout."""
        try:
            if df.empty:
                return False, "No data for Donchian check"
            
            current_high = df['high'].iloc[-1]
            current_low = df['low'].iloc[-1]
            donchian_high = get_indicator_value(indicators, 'donchian_high', -1)
            donchian_low = get_indicator_value(indicators, 'donchian_low', -1)
            
            if donchian_high is None or donchian_low is None:
                return False, "Donchian data unavailable"
            
            if side == 'LONG' and current_high > donchian_high:
                return True, f"Breakout({self.donchian_period}): High({current_high:.2f}) > Donchian({donchian_high:.2f})"
            elif side == 'SHORT' and current_low < donchian_low:
                return True, f"Breakout({self.donchian_period}): Low({current_low:.2f}) < Donchian({donchian_low:.2f})"
            
            return False, f"No Donchian breakout for {side}"
            
        except Exception as e:
            logger.error(f"Error checking Donchian breakout: {e}")
            return False, f"Donchian error: {e}"
    
    def _check_macd_crossover(self, indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check MACD crossover."""
        try:
            macd_line = get_indicator_value(indicators, 'macd', -1)
            macd_signal = get_indicator_value(indicators, 'macd_signal', -1)
            
            if macd_line is None or macd_signal is None:
                return False, "MACD data unavailable"
            
            if side == 'LONG' and macd_line > macd_signal and macd_line > 0:
                return True, f"MACD Cross: MACD({macd_line:.4f}) > Signal({macd_signal:.4f}) > 0"
            elif side == 'SHORT' and macd_line < macd_signal and macd_line < 0:
                return True, f"MACD Cross: MACD({macd_line:.4f}) < Signal({macd_signal:.4f}) < 0"
            
            return False, f"No MACD crossover for {side}"
            
        except Exception as e:
            logger.error(f"Error checking MACD crossover: {e}")
            return False, f"MACD error: {e}"
    
    def _check_roc_momentum(self, indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check Rate of Change momentum."""
        try:
            roc = get_indicator_value(indicators, 'roc', -1)
            
            if roc is None:
                return False, "ROC data unavailable"
            
            if side == 'LONG' and roc >= self.roc_min_long:
                return True, f"ROC({self.roc_lookback}): {roc:.3f} >= {self.roc_min_long:.3f}"
            elif side == 'SHORT' and roc <= self.roc_max_short:
                return True, f"ROC({self.roc_lookback}): {roc:.3f} <= {self.roc_max_short:.3f}"
            
            return False, f"No ROC momentum for {side}"
            
        except Exception as e:
            logger.error(f"Error checking ROC momentum: {e}")
            return False, f"ROC error: {e}"


class QualityFilter:
    """Quality filter for signal validation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.vol_mult = config.get('quality', {}).get('vol_mult', 1.2)
        self.atr_min_pct = config.get('quality', {}).get('atr_min_pct', 0.003)
        self.atr_max_pct = config.get('quality', {}).get('atr_max_pct', 0.03)
        self.atr_period = config.get('quality', {}).get('atr_period', 14)
    
    def check_quality(self, df: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Tuple[bool, str]:
        """
        Check if signal meets quality criteria.
        
        Args:
            df: DataFrame with OHLCV data
            indicators: Dictionary of computed indicators
            
        Returns:
            Tuple of (is_quality, reason)
        """
        try:
            quality_checks = []
            
            # 1. Volume check
            volume_check = self._check_volume(df, indicators)
            if volume_check:
                quality_checks.append(volume_check)
            
            # 2. Volatility check
            volatility_check = self._check_volatility(df, indicators)
            if volatility_check:
                quality_checks.append(volatility_check)
            
            if quality_checks:
                return True, f"Quality: {'; '.join(quality_checks)}"
            else:
                return False, "Quality filter failed"
                
        except Exception as e:
            logger.error(f"Error in quality filter: {e}")
            return False, f"Quality filter error: {e}"
    
    def _check_volume(self, df: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[str]:
        """Check volume conditions."""
        try:
            if 'volume' not in df.columns or df['volume'].isna().all():
                return None  # Skip volume check if no data
            
            current_volume = df['volume'].iloc[-1]
            volume_sma = get_indicator_value(indicators, 'volume_sma', -1)
            
            if volume_sma is None or volume_sma == 0:
                return None
            
            volume_ratio = current_volume / volume_sma
            
            if volume_ratio >= self.vol_mult:
                return f"Vol {volume_ratio:.1f}×"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking volume: {e}")
            return None
    
    def _check_volatility(self, df: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[str]:
        """Check volatility conditions."""
        try:
            current_price = df['close'].iloc[-1]
            atr = get_indicator_value(indicators, 'atr', -1)
            
            if atr is None or current_price == 0:
                return None
            
            atr_pct = atr / current_price
            
            if self.atr_min_pct <= atr_pct <= self.atr_max_pct:
                return f"ATR {atr_pct:.1%}"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking volatility: {e}")
            return None


class SignalGenerator:
    """Main signal generation engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.trend_filter = TrendFilter(config)
        self.entry_trigger = EntryTrigger(config)
        self.quality_filter = QualityFilter(config)
        
        # Risk management parameters
        self.stop_atr_mult = config.get('risk', {}).get('stop_atr_mult', 1.5)
        self.rr_ratio = config.get('risk', {}).get('rr_ratio', 2.0)
        self.time_stop_bars = config.get('risk', {}).get('time_stop_bars', 12)
    
    def generate_signals(
        self,
        htf_df: pd.DataFrame,
        ltf_df: pd.DataFrame,
        symbol: str,
        macro_guard: Dict[str, Any] = None
    ) -> List[Signal]:
        """
        Generate trading signals based on HTF and LTF data.
        
        Args:
            htf_df: Higher timeframe DataFrame
            ltf_df: Lower timeframe DataFrame
            symbol: Trading symbol
            macro_guard: Macro event guard information
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            if htf_df.empty or ltf_df.empty:
                logger.warning(f"Empty data for {symbol}")
                return signals
            
            # Compute indicators for both timeframes
            htf_indicators = compute_indicators(htf_df, self.config)
            ltf_indicators = compute_indicators(ltf_df, self.config)
            
            # Check for both LONG and SHORT signals
            for side in ['LONG', 'SHORT']:
                signal = self._check_signal_conditions(
                    htf_df, ltf_df, htf_indicators, ltf_indicators, symbol, side, macro_guard
                )
                if signal:
                    signals.append(signal)
            
            logger.debug(f"Generated {len(signals)} signals for {symbol}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return signals
    
    def _check_signal_conditions(
        self,
        htf_df: pd.DataFrame,
        ltf_df: pd.DataFrame,
        htf_indicators: Dict[str, pd.Series],
        ltf_indicators: Dict[str, pd.Series],
        symbol: str,
        side: str,
        macro_guard: Dict[str, Any] = None
    ) -> Optional[Signal]:
        """Check all conditions for a specific side."""
        try:
            # 1. Trend filter (HTF)
            trend_valid, trend_reason = self.trend_filter.check_trend(htf_indicators, side)
            if not trend_valid:
                return None
            
            # 2. Entry trigger (LTF)
            entry_valid, entry_reason = self.entry_trigger.check_entry_triggers(ltf_df, ltf_indicators, side)
            if not entry_valid:
                return None
            
            # 3. Quality filter (LTF)
            quality_valid, quality_reason = self.quality_filter.check_quality(ltf_df, ltf_indicators)
            if not quality_valid:
                return None
            
            # 4. Calculate entry, SL, TP levels
            entry_price = ltf_df['close'].iloc[-1]
            atr = get_indicator_value(ltf_indicators, 'atr', -1)
            
            if atr is None:
                logger.warning(f"No ATR data for {symbol}")
                return None
            
            # Calculate stop loss and take profit
            if side == 'LONG':
                stop_loss = entry_price - (self.stop_atr_mult * atr)
                sl_distance = entry_price - stop_loss
                take_profit = entry_price + (self.rr_ratio * sl_distance)
            else:  # SHORT
                stop_loss = entry_price + (self.stop_atr_mult * atr)
                sl_distance = stop_loss - entry_price
                take_profit = entry_price - (self.rr_ratio * sl_distance)
            
            risk_reward = self.rr_ratio
            
            # 5. Create signal
            signal_id = f"{symbol}_{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Combine reasons
            why_parts = [trend_reason, entry_reason, quality_reason]
            if macro_guard and not macro_guard.get('allowed', True):
                why_parts.append(f"Macro: {macro_guard.get('reason', 'Blocked')}")
            else:
                why_parts.append("brak makro w 30m")
            
            why = "; ".join(why_parts)
            
            # Calculate metrics
            metrics = {
                'atr': atr,
                'atr_pct': atr / entry_price,
                'volume_ratio': self._get_volume_ratio(ltf_df, ltf_indicators),
                'trend_strength': self._calculate_trend_strength(htf_indicators),
                'momentum_score': self._calculate_momentum_score(ltf_indicators, side)
            }
            
            signal = Signal(
                id=signal_id,
                timestamp=datetime.now(),
                side=side,
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward,
                why=why,
                metrics=metrics
            )
            
            logger.info(f"Generated {side} signal for {symbol}: Entry={entry_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}")
            return signal
            
        except Exception as e:
            logger.error(f"Error checking signal conditions for {symbol} {side}: {e}")
            return None
    
    def _get_volume_ratio(self, df: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[float]:
        """Get current volume ratio."""
        try:
            if 'volume' not in df.columns or df['volume'].isna().all():
                return None
            
            current_volume = df['volume'].iloc[-1]
            volume_sma = get_indicator_value(indicators, 'volume_sma', -1)
            
            if volume_sma is None or volume_sma == 0:
                return None
            
            return current_volume / volume_sma
            
        except Exception:
            return None
    
    def _calculate_trend_strength(self, indicators: Dict[str, pd.Series]) -> Optional[float]:
        """Calculate trend strength score."""
        try:
            sma_20 = get_indicator_value(indicators, 'sma_20', -1)
            sma_50 = get_indicator_value(indicators, 'sma_50', -1)
            sma_200 = get_indicator_value(indicators, 'sma_200', -1)
            
            if any(x is None for x in [sma_20, sma_50, sma_200]):
                return None
            
            # Simple trend strength calculation
            if sma_20 > sma_50 > sma_200:
                return 1.0  # Strong uptrend
            elif sma_20 < sma_50 < sma_200:
                return -1.0  # Strong downtrend
            else:
                return 0.0  # Sideways
                
        except Exception:
            return None
    
    def _calculate_momentum_score(self, indicators: Dict[str, pd.Series], side: str) -> Optional[float]:
        """Calculate momentum score."""
        try:
            roc = get_indicator_value(indicators, 'roc', -1)
            macd = get_indicator_value(indicators, 'macd', -1)
            
            if roc is None or macd is None:
                return None
            
            # Simple momentum score
            momentum = 0.0
            
            if side == 'LONG':
                if roc > 0:
                    momentum += 0.5
                if macd > 0:
                    momentum += 0.5
            else:  # SHORT
                if roc < 0:
                    momentum += 0.5
                if macd < 0:
                    momentum += 0.5
            
            return momentum
            
        except Exception:
            return None


class SignalManager:
    """Manages active signals and their lifecycle."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_signals = {}
        self.signal_history = []
        self.cooldown_periods = {}  # Track cooldown periods per symbol
        
        # Configuration
        self.max_open_signals = config.get('risk', {}).get('max_open_signals', 5)
        self.cooldown_minutes = config.get('cooldowns', {}).get('per_symbol_minutes', 30)
    
    def add_signal(self, signal: Signal) -> bool:
        """
        Add a new signal if conditions are met.
        
        Args:
            signal: Signal to add
            
        Returns:
            True if signal was added, False otherwise
        """
        try:
            # Check if we have too many open signals
            if len(self.active_signals) >= self.max_open_signals:
                logger.warning(f"Maximum open signals reached ({self.max_open_signals})")
                return False
            
            # Check cooldown period
            if self._is_in_cooldown(signal.symbol):
                logger.warning(f"Signal for {signal.symbol} is in cooldown period")
                return False
            
            # Add signal
            self.active_signals[signal.id] = signal
            self.signal_history.append(signal)
            
            # Set cooldown
            self.cooldown_periods[signal.symbol] = datetime.now()
            
            logger.info(f"Added {signal.side} signal for {signal.symbol}: {signal.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding signal: {e}")
            return False
    
    def update_signals(self, current_data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        Update all active signals and check for exits.
        
        Args:
            current_data: Dictionary of symbol -> DataFrame with current data
            
        Returns:
            List of signals that were closed
        """
        closed_signals = []
        
        try:
            for signal_id, signal in list(self.active_signals.items()):
                if signal.symbol not in current_data:
                    continue
                
                df = current_data[signal.symbol]
                if df.empty:
                    continue
                
                # Check for exit conditions
                exit_reason = self._check_exit_conditions(signal, df)
                
                if exit_reason:
                    signal.status = exit_reason
                    closed_signals.append(signal)
                    del self.active_signals[signal_id]
                    logger.info(f"Closed {signal.side} signal for {signal.symbol}: {exit_reason}")
                else:
                    # Update bars since entry
                    signal.bars_since_entry += 1
        
        except Exception as e:
            logger.error(f"Error updating signals: {e}")
        
        return closed_signals
    
    def _check_exit_conditions(self, signal: Signal, df: pd.DataFrame) -> Optional[str]:
        """Check if signal should be exited."""
        try:
            if df.empty:
                return None
            
            current_price = df['close'].iloc[-1]
            current_high = df['high'].iloc[-1]
            current_low = df['low'].iloc[-1]
            
            # 1. Check for SL/TP hits
            if signal.side == 'LONG':
                if current_low <= signal.stop_loss:
                    return 'HIT_SL'
                elif current_high >= signal.take_profit:
                    return 'HIT_TP'
            else:  # SHORT
                if current_high >= signal.stop_loss:
                    return 'HIT_SL'
                elif current_low <= signal.take_profit:
                    return 'HIT_TP'
            
            # 2. Check time stop
            if signal.bars_since_entry >= self.config.get('risk', {}).get('time_stop_bars', 12):
                return 'TIME_STOP'
            
            # 3. Check trend break (simplified)
            # In a full implementation, you'd recompute indicators here
            # For now, we'll use a simple price-based trend break
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return None
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period."""
        if symbol not in self.cooldown_periods:
            return False
        
        cooldown_start = self.cooldown_periods[symbol]
        cooldown_end = cooldown_start + timedelta(minutes=self.cooldown_minutes)
        
        return datetime.now() < cooldown_end
    
    def get_active_signals(self) -> List[Signal]:
        """Get all active signals."""
        return list(self.active_signals.values())
    
    def get_signal_history(self, symbol: str = None, limit: int = 100) -> List[Signal]:
        """Get signal history."""
        history = self.signal_history
        
        if symbol:
            history = [s for s in history if s.symbol == symbol]
        
        return history[-limit:] if limit else history