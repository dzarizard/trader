"""
Position sizing and risk management for CFD Trader Assistant.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class PositionPlan(BaseModel):
    """Position sizing plan."""
    size_units: float
    risk_amount: float
    risk_pct: float
    value_per_point: float
    max_loss: float
    potential_profit: float
    position_value: float
    margin_required: float
    leverage: float


class Instrument:
    """Trading instrument configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.symbol = config['symbol']
        self.kind = config['kind']  # 'fx', 'index', 'commodity', 'stock'
        self.point_value = config.get('point_value', 1.0)
        self.pip_value = config.get('pip_value', 10.0)
        self.min_step = config.get('min_step', 0.0001)
        self.lot_size = config.get('lot_size', 100000)  # Standard lot size
        self.margin_requirement = config.get('margin_requirement', 0.01)  # 1% margin
        self.leverage = config.get('leverage', 100)
    
    def get_point_value(self, side: str) -> float:
        """Get point value for the given side."""
        return self.point_value
    
    def get_pip_value(self, side: str) -> float:
        """Get pip value for the given side."""
        return self.pip_value
    
    def calculate_pip_distance(self, entry_price: float, exit_price: float) -> float:
        """Calculate pip distance between two prices."""
        if self.kind == 'fx':
            # For FX, pip is usually 0.0001 for major pairs
            return abs(exit_price - entry_price) / self.min_step
        else:
            # For indices and commodities, use point value
            return abs(exit_price - entry_price) / self.min_step
    
    def calculate_position_value(self, size_units: float, price: float) -> float:
        """Calculate total position value."""
        if self.kind == 'fx':
            return size_units * self.lot_size * price
        else:
            return size_units * price * self.point_value


class Account:
    """Trading account configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.equity = config.get('initial_equity', 10000)
        self.currency = config.get('equity_ccy', 'USD')
        self.risk_per_trade_pct = config.get('risk_management', {}).get('risk_per_trade_pct', 0.008)
        self.max_daily_loss_pct = config.get('risk_management', {}).get('max_daily_loss_pct', 0.02)
        self.max_open_signals = config.get('risk_management', {}).get('max_open_signals', 5)
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
    
    def reset_daily_stats(self):
        """Reset daily statistics."""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = current_date
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if account can take new trades."""
        self.reset_daily_stats()
        
        # Check daily loss limit
        if self.daily_pnl <= -self.equity * self.max_daily_loss_pct:
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f}"
        
        return True, "Account can trade"
    
    def get_available_risk(self) -> float:
        """Get available risk amount for new trades."""
        self.reset_daily_stats()
        
        # Calculate remaining daily risk
        max_daily_risk = self.equity * self.max_daily_loss_pct
        remaining_daily_risk = max_daily_risk + self.daily_pnl  # daily_pnl is negative when losing
        
        # Use the smaller of per-trade risk or remaining daily risk
        per_trade_risk = self.equity * self.risk_per_trade_pct
        
        return min(per_trade_risk, max(0, remaining_daily_risk))


class PositionSizer:
    """Position sizing calculator."""
    
    def __init__(self, account: Account):
        self.account = account
    
    def calculate_position_size(
        self,
        signal,
        instrument: Instrument,
        current_price: float = None
    ) -> PositionPlan:
        """
        Calculate optimal position size for a signal.
        
        Args:
            signal: Trading signal
            instrument: Instrument configuration
            current_price: Current market price (if different from entry)
            
        Returns:
            PositionPlan with sizing details
        """
        try:
            if current_price is None:
                current_price = signal.entry_price
            
            # Get available risk
            available_risk = self.account.get_available_risk()
            
            # Calculate risk per unit
            if signal.side == 'LONG':
                risk_per_unit = current_price - signal.stop_loss
            else:  # SHORT
                risk_per_unit = signal.stop_loss - current_price
            
            if risk_per_unit <= 0:
                logger.warning(f"Invalid risk per unit: {risk_per_unit}")
                return self._create_empty_plan()
            
            # Calculate position size based on risk
            if instrument.kind == 'fx':
                # For FX, calculate lot size
                pip_risk = instrument.calculate_pip_distance(current_price, signal.stop_loss)
                pip_value = instrument.get_pip_value(signal.side)
                risk_per_lot = pip_risk * pip_value
                
                if risk_per_lot > 0:
                    lot_size = available_risk / risk_per_lot
                    # Round to standard lot sizes (0.01, 0.1, 1.0, etc.)
                    lot_size = self._round_to_lot_size(lot_size)
                else:
                    lot_size = 0.01  # Minimum lot size
                
                size_units = lot_size
                value_per_point = pip_value
                
            else:
                # For indices and commodities
                point_risk = risk_per_unit / instrument.min_step
                risk_per_unit_value = point_risk * instrument.point_value
                
                if risk_per_unit_value > 0:
                    size_units = available_risk / risk_per_unit_value
                    # Round to reasonable size
                    size_units = round(size_units, 2)
                else:
                    size_units = 1.0  # Minimum size
                
                value_per_point = instrument.point_value
            
            # Calculate position metrics
            position_value = instrument.calculate_position_value(size_units, current_price)
            risk_amount = size_units * risk_per_unit * value_per_point
            risk_pct = (risk_amount / self.account.equity) * 100
            
            # Calculate potential profit
            if signal.side == 'LONG':
                profit_per_unit = signal.take_profit - current_price
            else:  # SHORT
                profit_per_unit = current_price - signal.take_profit
            
            potential_profit = size_units * profit_per_unit * value_per_point
            
            # Calculate margin requirements
            margin_required = position_value * instrument.margin_requirement
            leverage = position_value / margin_required if margin_required > 0 else 0
            
            return PositionPlan(
                size_units=size_units,
                risk_amount=risk_amount,
                risk_pct=risk_pct,
                value_per_point=value_per_point,
                max_loss=risk_amount,
                potential_profit=potential_profit,
                position_value=position_value,
                margin_required=margin_required,
                leverage=leverage
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self._create_empty_plan()
    
    def _round_to_lot_size(self, lot_size: float) -> float:
        """Round lot size to standard values."""
        if lot_size < 0.01:
            return 0.01
        elif lot_size < 0.1:
            return round(lot_size, 2)
        elif lot_size < 1.0:
            return round(lot_size, 1)
        else:
            return round(lot_size)
    
    def _create_empty_plan(self) -> PositionPlan:
        """Create an empty position plan."""
        return PositionPlan(
            size_units=0.0,
            risk_amount=0.0,
            risk_pct=0.0,
            value_per_point=0.0,
            max_loss=0.0,
            potential_profit=0.0,
            position_value=0.0,
            margin_required=0.0,
            leverage=0.0
        )


class RiskManager:
    """Risk management and portfolio monitoring."""
    
    def __init__(self, account: Account):
        self.account = account
        self.active_positions = {}
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0
        }
    
    def validate_signal(self, signal, instrument: Instrument) -> Tuple[bool, str]:
        """
        Validate if a signal meets risk management criteria.
        
        Args:
            signal: Trading signal
            instrument: Instrument configuration
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Check if account can trade
            can_trade, reason = self.account.can_trade()
            if not can_trade:
                return False, reason
            
            # Check maximum open signals
            if len(self.active_positions) >= self.account.max_open_signals:
                return False, f"Maximum open signals reached ({self.account.max_open_signals})"
            
            # Check if we already have a position in this symbol
            if signal.symbol in self.active_positions:
                return False, f"Already have position in {signal.symbol}"
            
            # Calculate position size to validate risk
            sizer = PositionSizer(self.account)
            position_plan = sizer.calculate_position_size(signal, instrument)
            
            # Check if position size is reasonable
            if position_plan.size_units <= 0:
                return False, "Invalid position size calculated"
            
            # Check risk percentage
            if position_plan.risk_pct > self.account.risk_per_trade_pct * 100 * 1.1:  # 10% tolerance
                return False, f"Risk too high: {position_plan.risk_pct:.2f}%"
            
            # Check leverage
            if position_plan.leverage > instrument.leverage * 1.1:  # 10% tolerance
                return False, f"Leverage too high: {position_plan.leverage:.1f}x"
            
            return True, "Signal validated"
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False, f"Validation error: {e}"
    
    def add_position(self, signal, position_plan: PositionPlan, instrument: Instrument):
        """Add a new position to tracking."""
        try:
            position_data = {
                'signal': signal,
                'position_plan': position_plan,
                'instrument': instrument,
                'entry_time': datetime.now(),
                'status': 'OPEN',
                'current_pnl': 0.0,
                'max_favorable': 0.0,
                'max_adverse': 0.0
            }
            
            self.active_positions[signal.id] = position_data
            self.daily_stats['trades'] += 1
            
            logger.info(f"Added position for {signal.symbol}: {position_plan.size_units} units, risk: {position_plan.risk_amount:.2f}")
            
        except Exception as e:
            logger.error(f"Error adding position: {e}")
    
    def update_positions(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Update all active positions with current prices.
        
        Args:
            current_prices: Dictionary of symbol -> current price
            
        Returns:
            List of closed positions
        """
        closed_positions = []
        
        try:
            for position_id, position_data in list(self.active_positions.items()):
                signal = position_data['signal']
                position_plan = position_data['position_plan']
                instrument = position_data['instrument']
                
                if signal.symbol not in current_prices:
                    continue
                
                current_price = current_prices[signal.symbol]
                
                # Calculate current P&L
                if signal.side == 'LONG':
                    pnl_per_unit = current_price - signal.entry_price
                else:  # SHORT
                    pnl_per_unit = signal.entry_price - current_price
                
                current_pnl = pnl_per_unit * position_plan.size_units * position_plan.value_per_point
                position_data['current_pnl'] = current_pnl
                
                # Update max favorable/adverse
                if current_pnl > position_data['max_favorable']:
                    position_data['max_favorable'] = current_pnl
                if current_pnl < position_data['max_adverse']:
                    position_data['max_adverse'] = current_pnl
                
                # Check for exit conditions
                should_exit, exit_reason = self._check_position_exit(signal, current_price, position_data)
                
                if should_exit:
                    # Close position
                    position_data['status'] = 'CLOSED'
                    position_data['exit_time'] = datetime.now()
                    position_data['exit_reason'] = exit_reason
                    position_data['final_pnl'] = current_pnl
                    
                    # Update daily stats
                    self.daily_stats['total_pnl'] += current_pnl
                    if current_pnl > 0:
                        self.daily_stats['wins'] += 1
                    else:
                        self.daily_stats['losses'] += 1
                    
                    # Update account
                    self.account.daily_pnl += current_pnl
                    
                    closed_positions.append(position_data)
                    del self.active_positions[position_id]
                    
                    logger.info(f"Closed position for {signal.symbol}: {exit_reason}, P&L: {current_pnl:.2f}")
        
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
        
        return closed_positions
    
    def _check_position_exit(self, signal, current_price: float, position_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if position should be exited."""
        try:
            # Check SL/TP hits
            if signal.side == 'LONG':
                if current_price <= signal.stop_loss:
                    return True, 'HIT_SL'
                elif current_price >= signal.take_profit:
                    return True, 'HIT_TP'
            else:  # SHORT
                if current_price >= signal.stop_loss:
                    return True, 'HIT_SL'
                elif current_price <= signal.take_profit:
                    return True, 'HIT_TP'
            
            # Check time stop
            entry_time = position_data['entry_time']
            time_elapsed = datetime.now() - entry_time
            max_hold_time = signal.metrics.get('max_hold_hours', 24)  # Default 24 hours
            
            if time_elapsed.total_seconds() / 3600 > max_hold_time:
                return True, 'TIME_STOP'
            
            # Check trailing stop (if implemented)
            # This would require additional logic for trailing stops
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking position exit: {e}")
            return False, None
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary statistics."""
        try:
            total_exposure = sum(
                pos['position_plan'].position_value 
                for pos in self.active_positions.values()
            )
            
            total_risk = sum(
                pos['position_plan'].risk_amount 
                for pos in self.active_positions.values()
            )
            
            total_pnl = sum(
                pos['current_pnl'] 
                for pos in self.active_positions.values()
            )
            
            # Calculate win rate
            total_trades = self.daily_stats['wins'] + self.daily_stats['losses']
            win_rate = (self.daily_stats['wins'] / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'account_equity': self.account.equity,
                'daily_pnl': self.account.daily_pnl,
                'total_exposure': total_exposure,
                'total_risk': total_risk,
                'total_pnl': total_pnl,
                'active_positions': len(self.active_positions),
                'max_positions': self.account.max_open_signals,
                'win_rate': win_rate,
                'daily_trades': self.daily_stats['trades'],
                'daily_wins': self.daily_stats['wins'],
                'daily_losses': self.daily_stats['losses']
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    def get_position_details(self, position_id: str = None) -> Dict[str, Any]:
        """Get detailed position information."""
        if position_id:
            return self.active_positions.get(position_id, {})
        else:
            return self.active_positions