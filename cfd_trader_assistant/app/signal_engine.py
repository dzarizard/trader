"""
Unified signal generation engine for CFD Trader Assistant.
Eliminates look-ahead bias and provides consistent logic for both live and backtest modes.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
import logging

from .indicators import compute_indicators, get_indicator_value, is_indicator_above, is_indicator_below
from .pricing import PricingEngine, FeesModel

logger = logging.getLogger(__name__)


class Signal(BaseModel):
    """Trading signal model with enhanced fields."""
    id: str
    timestamp: datetime
    side: str  # 'LONG' or 'SHORT'
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    net_risk_reward_ratio: float
    why: str
    metrics: Dict[str, Any]
    status: str = 'ACTIVE'  # 'ACTIVE', 'HIT_SL', 'HIT_TP', 'TIME_STOP', 'TREND_BREAK'
    bars_since_entry: int = 0
    entry_costs: float = 0.0
    exit_costs: float = 0.0
    net_pnl: float = 0.0


class SignalState(BaseModel):
    """State tracking for signals to prevent spam."""
    last_signal_id: Optional[str] = None
    last_signal_time: Optional[datetime] = None
    last_entry_price: Optional[float] = None
    last_stop_loss: Optional[float] = None
    last_take_profit: Optional[float] = None
    cooldown_until: Optional[datetime] = None


class SignalEngine:
    """Unified signal generation engine with anti look-ahead bias."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pricing_engine = PricingEngine(config)
        self.fees_model = FeesModel(config.get('fees', {}))
        
        # Signal state tracking per symbol
        self.signal_states: Dict[str, SignalState] = {}
        
        # Configuration
        self.trend_config = config.get('trend', {})
        self.entry_config = config.get('entry', {})
        self.quality_config = config.get('quality', {})
        self.risk_config = config.get('risk', {})
        self.cooldown_config = config.get('cooldowns', {})
    
    def generate_signals(
        self,
        htf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
        symbol: str,
        instrument_config: Dict[str, Any],
        macro_guard: Dict[str, Any] = None
    ) -> List[Signal]:
        """
        Generate trading signals with anti look-ahead bias.
        
        Args:
            htf_data: Higher timeframe data (must be closed bars only)
            ltf_data: Lower timeframe data (current bar may be incomplete)
            symbol: Trading symbol
            instrument_config: Instrument configuration
            macro_guard: Macro event guard information
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            if htf_data.empty or ltf_data.empty:
                logger.warning(f"Empty data for {symbol}")
                return signals
            
            # Ensure we only use closed bars (anti look-ahead bias)
            htf_closed = self._get_closed_bars(htf_data)
            ltf_closed = self._get_closed_bars(ltf_data)
            
            if len(htf_closed) < 200 or len(ltf_closed) < 50:
                logger.warning(f"Insufficient closed bars for {symbol}: HTF={len(htf_closed)}, LTF={len(ltf_closed)}")
                return signals
            
            # Compute indicators for both timeframes
            htf_indicators = compute_indicators(htf_closed, self.config)
            ltf_indicators = compute_indicators(ltf_closed, self.config)
            
            # Apply HTF shift to prevent look-ahead bias
            htf_indicators_shifted = self._shift_htf_indicators(htf_indicators)
            
            # Check for both LONG and SHORT signals
            for side in ['LONG', 'SHORT']:
                signal = self._check_signal_conditions(
                    htf_closed, ltf_closed, htf_indicators_shifted, ltf_indicators,
                    symbol, side, instrument_config, macro_guard
                )
                if signal:
                    signals.append(signal)
            
            logger.debug(f"Generated {len(signals)} signals for {symbol}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return signals
    
    def _get_closed_bars(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get only closed bars (exclude current incomplete bar).
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with only closed bars
        """
        if df.empty:
            return df
        
        # For backtesting, all bars are closed
        # For live trading, exclude the last bar if it's the current incomplete bar
        # This is determined by checking if the last bar's timestamp is in the future
        current_time = datetime.now()
        
        # If the last bar's timestamp is very recent (within last 5 minutes), consider it incomplete
        last_timestamp = df['timestamp'].iloc[-1]
        if isinstance(last_timestamp, pd.Timestamp):
            last_timestamp = last_timestamp.to_pydatetime()
        
        time_diff = (current_time - last_timestamp).total_seconds()
        
        # If the last bar is very recent, exclude it to prevent look-ahead bias
        if time_diff < 300:  # 5 minutes
            return df.iloc[:-1]
        
        return df
    
    def _shift_htf_indicators(self, htf_indicators: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """
        Shift HTF indicators by 1 bar to prevent look-ahead bias.
        
        Args:
            htf_indicators: HTF indicators
            
        Returns:
            Shifted HTF indicators
        """
        shifted_indicators = {}
        
        for name, series in htf_indicators.items():
            # Shift by 1 bar to prevent look-ahead bias
            shifted_indicators[name] = series.shift(1)
        
        return shifted_indicators
    
    def _check_signal_conditions(
        self,
        htf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
        htf_indicators: Dict[str, pd.Series],
        ltf_indicators: Dict[str, pd.Series],
        symbol: str,
        side: str,
        instrument_config: Dict[str, Any],
        macro_guard: Dict[str, Any] = None
    ) -> Optional[Signal]:
        """Check all conditions for a specific side."""
        try:
            # 1. Trend filter (HTF) - using shifted indicators
            trend_valid, trend_reason = self._check_trend_filter(htf_indicators, side)
            if not trend_valid:
                return None
            
            # 2. Entry trigger (LTF)
            entry_valid, entry_reason = self._check_entry_triggers(ltf_data, ltf_indicators, side)
            if not entry_valid:
                return None
            
            # 3. Quality filter (LTF)
            quality_valid, quality_reason = self._check_quality_filter(ltf_data, ltf_indicators)
            if not quality_valid:
                return None
            
            # 4. Macro guard
            if macro_guard and not macro_guard.get('allowed', True):
                logger.debug(f"Signal blocked by macro guard for {symbol}")
                return None
            
            # 5. Cooldown check
            if self._is_in_cooldown(symbol):
                logger.debug(f"Signal blocked by cooldown for {symbol}")
                return None
            
            # 6. Calculate entry, SL, TP levels with proper rounding
            entry_price = ltf_data['close'].iloc[-1]
            atr = get_indicator_value(ltf_indicators, 'atr', -1)
            
            if atr is None:
                logger.warning(f"No ATR data for {symbol}")
                return None
            
            # Get instrument parameters
            min_step = instrument_config.get('min_step', 0.0001)
            point_value = instrument_config.get('point_value', 1.0)
            pip_value = instrument_config.get('pip_value', 10.0)
            
            # Calculate stop loss and take profit
            if side == 'LONG':
                stop_loss = entry_price - (self.risk_config.get('stop_atr_mult', 1.5) * atr)
                sl_distance = entry_price - stop_loss
                take_profit = entry_price + (self.risk_config.get('rr_ratio', 2.0) * sl_distance)
            else:  # SHORT
                stop_loss = entry_price + (self.risk_config.get('stop_atr_mult', 1.5) * atr)
                sl_distance = stop_loss - entry_price
                take_profit = entry_price - (self.risk_config.get('rr_ratio', 2.0) * sl_distance)
            
            # Round prices to tick size
            entry_price = self.pricing_engine.round_price(entry_price, min_step)
            stop_loss = self.pricing_engine.round_price(stop_loss, min_step)
            take_profit = self.pricing_engine.round_price(take_profit, min_step)
            
            # Validate price levels
            is_valid, reason = self.pricing_engine.validate_price_levels(entry_price, stop_loss, take_profit, min_step)
            if not is_valid:
                logger.warning(f"Invalid price levels for {symbol}: {reason}")
                return None
            
            # Calculate risk-reward ratios
            gross_rr = self.pricing_engine.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
            
            # Calculate costs
            position_size = 1.0  # Will be calculated by sizing engine
            position_value = self.pricing_engine.calculate_position_value(entry_price, position_size, point_value)
            entry_costs = self.fees_model.calculate_total_costs(position_size, position_value, pip_value)
            exit_costs = self.fees_model.calculate_total_costs(position_size, position_value, pip_value)
            
            # Calculate net risk-reward
            risk_amount = abs(entry_price - stop_loss) * position_size * point_value
            net_rr = self.fees_model.calculate_net_risk_reward(gross_rr, entry_costs, exit_costs, risk_amount)
            
            # 7. Create signal
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
                'volume_ratio': self._get_volume_ratio(ltf_data, ltf_indicators),
                'trend_strength': self._calculate_trend_strength(htf_indicators),
                'momentum_score': self._calculate_momentum_score(ltf_indicators, side),
                'gross_rr': gross_rr,
                'net_rr': net_rr,
                'entry_costs': entry_costs,
                'exit_costs': exit_costs
            }
            
            signal = Signal(
                id=signal_id,
                timestamp=datetime.now(),
                side=side,
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=gross_rr,
                net_risk_reward_ratio=net_rr,
                why=why,
                metrics=metrics,
                entry_costs=entry_costs,
                exit_costs=exit_costs
            )
            
            # Update signal state
            self._update_signal_state(symbol, signal)
            
            logger.info(f"Generated {side} signal for {symbol}: Entry={entry_price:.4f}, SL={stop_loss:.4f}, TP={take_profit:.4f}, RR={gross_rr:.2f}")
            return signal
            
        except Exception as e:
            logger.error(f"Error checking signal conditions for {symbol} {side}: {e}")
            return None
    
    def _check_trend_filter(self, htf_indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check trend filter conditions."""
        try:
            close_price = get_indicator_value(htf_indicators, 'close', -1)
            sma_200 = get_indicator_value(htf_indicators, 'sma_200', -1)
            sma_50 = get_indicator_value(htf_indicators, 'sma_50', -1)
            sma_20 = get_indicator_value(htf_indicators, 'sma_20', -1)
            
            if any(x is None for x in [close_price, sma_200, sma_50, sma_20]):
                return False, "Missing trend indicator data"
            
            if side == 'LONG':
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
    
    def _check_entry_triggers(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check entry trigger conditions."""
        try:
            triggers = []
            
            # 1. Donchian Channel Breakout
            donchian_trigger = self._check_donchian_breakout(ltf_data, ltf_indicators, side)
            if donchian_trigger[0]:
                triggers.append(donchian_trigger[1])
            
            # 2. MACD Crossover
            macd_trigger = self._check_macd_crossover(ltf_indicators, side)
            if macd_trigger[0]:
                triggers.append(macd_trigger[1])
            
            # 3. Rate of Change
            roc_trigger = self._check_roc_momentum(ltf_indicators, side)
            if roc_trigger[0]:
                triggers.append(roc_trigger[1])
            
            if triggers:
                return True, f"Trigger(LTF): {'; '.join(triggers)}"
            else:
                return False, "No entry triggers met"
                
        except Exception as e:
            logger.error(f"Error in entry trigger check: {e}")
            return False, f"Entry trigger error: {e}"
    
    def _check_donchian_breakout(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check Donchian Channel breakout."""
        try:
            if ltf_data.empty:
                return False, "No data for Donchian check"
            
            current_high = ltf_data['high'].iloc[-1]
            current_low = ltf_data['low'].iloc[-1]
            donchian_high = get_indicator_value(ltf_indicators, 'donchian_high', -1)
            donchian_low = get_indicator_value(ltf_indicators, 'donchian_low', -1)
            
            if donchian_high is None or donchian_low is None:
                return False, "Donchian data unavailable"
            
            donchian_period = self.entry_config.get('donchian_period', 20)
            
            if side == 'LONG' and current_high > donchian_high:
                return True, f"Breakout({donchian_period}): High({current_high:.2f}) > Donchian({donchian_high:.2f})"
            elif side == 'SHORT' and current_low < donchian_low:
                return True, f"Breakout({donchian_period}): Low({current_low:.2f}) < Donchian({donchian_low:.2f})"
            
            return False, f"No Donchian breakout for {side}"
            
        except Exception as e:
            logger.error(f"Error checking Donchian breakout: {e}")
            return False, f"Donchian error: {e}"
    
    def _check_macd_crossover(self, ltf_indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check MACD crossover."""
        try:
            macd_line = get_indicator_value(ltf_indicators, 'macd', -1)
            macd_signal = get_indicator_value(ltf_indicators, 'macd_signal', -1)
            
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
    
    def _check_roc_momentum(self, ltf_indicators: Dict[str, pd.Series], side: str) -> Tuple[bool, str]:
        """Check Rate of Change momentum."""
        try:
            roc = get_indicator_value(ltf_indicators, 'roc', -1)
            
            if roc is None:
                return False, "ROC data unavailable"
            
            roc_lookback = self.entry_config.get('roc_lookback', 10)
            roc_min_long = self.entry_config.get('roc_min_long', 0.003)
            roc_max_short = self.entry_config.get('roc_max_short', -0.003)
            
            if side == 'LONG' and roc >= roc_min_long:
                return True, f"ROC({roc_lookback}): {roc:.3f} >= {roc_min_long:.3f}"
            elif side == 'SHORT' and roc <= roc_max_short:
                return True, f"ROC({roc_lookback}): {roc:.3f} <= {roc_max_short:.3f}"
            
            return False, f"No ROC momentum for {side}"
            
        except Exception as e:
            logger.error(f"Error checking ROC momentum: {e}")
            return False, f"ROC error: {e}"
    
    def _check_quality_filter(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series]) -> Tuple[bool, str]:
        """Check quality filter conditions."""
        try:
            quality_checks = []
            
            # 1. Volume check
            volume_check = self._check_volume(ltf_data, ltf_indicators)
            if volume_check:
                quality_checks.append(volume_check)
            
            # 2. Volatility check
            volatility_check = self._check_volatility(ltf_data, ltf_indicators)
            if volatility_check:
                quality_checks.append(volatility_check)
            
            if quality_checks:
                return True, f"Quality: {'; '.join(quality_checks)}"
            else:
                return False, "Quality filter failed"
                
        except Exception as e:
            logger.error(f"Error in quality filter: {e}")
            return False, f"Quality filter error: {e}"
    
    def _check_volume(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series]) -> Optional[str]:
        """Check volume conditions."""
        try:
            if 'volume' not in ltf_data.columns or ltf_data['volume'].isna().all():
                return None  # Skip volume check if no data
            
            current_volume = ltf_data['volume'].iloc[-1]
            volume_sma = get_indicator_value(ltf_indicators, 'volume_sma', -1)
            
            if volume_sma is None or volume_sma == 0:
                return None
            
            vol_mult = self.quality_config.get('vol_mult', 1.2)
            volume_ratio = current_volume / volume_sma
            
            if volume_ratio >= vol_mult:
                return f"Vol {volume_ratio:.1f}×"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking volume: {e}")
            return None
    
    def _check_volatility(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series]) -> Optional[str]:
        """Check volatility conditions."""
        try:
            current_price = ltf_data['close'].iloc[-1]
            atr = get_indicator_value(ltf_indicators, 'atr', -1)
            
            if atr is None or current_price == 0:
                return None
            
            atr_pct = atr / current_price
            atr_min_pct = self.quality_config.get('atr_min_pct', 0.003)
            atr_max_pct = self.quality_config.get('atr_max_pct', 0.03)
            
            if atr_min_pct <= atr_pct <= atr_max_pct:
                return f"ATR {atr_pct:.1%}"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking volatility: {e}")
            return None
    
    def _get_volume_ratio(self, ltf_data: pd.DataFrame, ltf_indicators: Dict[str, pd.Series]) -> Optional[float]:
        """Get current volume ratio."""
        try:
            if 'volume' not in ltf_data.columns or ltf_data['volume'].isna().all():
                return None
            
            current_volume = ltf_data['volume'].iloc[-1]
            volume_sma = get_indicator_value(ltf_indicators, 'volume_sma', -1)
            
            if volume_sma is None or volume_sma == 0:
                return None
            
            return current_volume / volume_sma
            
        except Exception:
            return None
    
    def _calculate_trend_strength(self, htf_indicators: Dict[str, pd.Series]) -> Optional[float]:
        """Calculate trend strength score."""
        try:
            sma_20 = get_indicator_value(htf_indicators, 'sma_20', -1)
            sma_50 = get_indicator_value(htf_indicators, 'sma_50', -1)
            sma_200 = get_indicator_value(htf_indicators, 'sma_200', -1)
            
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
    
    def _calculate_momentum_score(self, ltf_indicators: Dict[str, pd.Series], side: str) -> Optional[float]:
        """Calculate momentum score."""
        try:
            roc = get_indicator_value(ltf_indicators, 'roc', -1)
            macd = get_indicator_value(ltf_indicators, 'macd', -1)
            
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
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period."""
        if symbol not in self.signal_states:
            return False
        
        state = self.signal_states[symbol]
        if state.cooldown_until is None:
            return False
        
        return datetime.now() < state.cooldown_until
    
    def _update_signal_state(self, symbol: str, signal: Signal):
        """Update signal state for cooldown tracking."""
        cooldown_minutes = self.cooldown_config.get('per_symbol_minutes', 30)
        cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        
        self.signal_states[symbol] = SignalState(
            last_signal_id=signal.id,
            last_signal_time=signal.timestamp,
            last_entry_price=signal.entry_price,
            last_stop_loss=signal.stop_loss,
            last_take_profit=signal.take_profit,
            cooldown_until=cooldown_until
        )
    
    def should_send_alert(self, signal: Signal) -> bool:
        """Check if alert should be sent (anti-spam)."""
        symbol = signal.symbol
        
        if symbol not in self.signal_states:
            return True
        
        state = self.signal_states[symbol]
        
        # Check if this is a new signal (different from last one)
        if (state.last_entry_price != signal.entry_price or
            state.last_stop_loss != signal.stop_loss or
            state.last_take_profit != signal.take_profit):
            return True
        
        # Check if enough time has passed since last signal
        if state.last_signal_time is None:
            return True
        
        time_since_last = (signal.timestamp - state.last_signal_time).total_seconds()
        min_interval = 300  # 5 minutes minimum between alerts
        
        return time_since_last >= min_interval