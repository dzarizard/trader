"""
Pricing and rounding utilities for CFD Trader Assistant.
"""
import math
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class PricingEngine:
    """Handles price rounding and position sizing calculations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def round_price(self, price: float, min_step: float) -> float:
        """
        Round price to the nearest tick size.
        
        Args:
            price: Price to round
            min_step: Minimum price step (tick size)
            
        Returns:
            Rounded price
        """
        if min_step <= 0:
            logger.warning(f"Invalid min_step: {min_step}, returning original price")
            return price
        
        # Calculate number of decimal places needed
        decimal_places = self._get_decimal_places(min_step)
        
        # Round to nearest tick
        rounded = round(price / min_step) * min_step
        
        # Round to appropriate decimal places
        return round(rounded, decimal_places)
    
    def round_size(self, size: float, lot_step: float) -> float:
        """
        Round position size to the nearest lot step.
        
        Args:
            size: Position size to round
            lot_step: Minimum lot step
            
        Returns:
            Rounded position size
        """
        if lot_step <= 0:
            logger.warning(f"Invalid lot_step: {lot_step}, returning original size")
            return size
        
        # Round to nearest lot step
        rounded = round(size / lot_step) * lot_step
        
        # Ensure minimum size
        return max(rounded, lot_step)
    
    def _get_decimal_places(self, step: float) -> int:
        """Get number of decimal places for a given step size."""
        if step >= 1:
            return 0
        elif step >= 0.1:
            return 1
        elif step >= 0.01:
            return 2
        elif step >= 0.001:
            return 3
        elif step >= 0.0001:
            return 4
        elif step >= 0.00001:
            return 5
        else:
            return 6
    
    def calculate_pip_distance(self, entry_price: float, exit_price: float, min_step: float) -> float:
        """
        Calculate pip/point distance between two prices.
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            min_step: Minimum price step
            
        Returns:
            Distance in pips/points
        """
        return abs(exit_price - entry_price) / min_step
    
    def calculate_pip_value(self, pip_distance: float, pip_value: float, position_size: float) -> float:
        """
        Calculate pip value for a position.
        
        Args:
            pip_distance: Distance in pips
            pip_value: Value per pip
            position_size: Position size
            
        Returns:
            Total pip value
        """
        return pip_distance * pip_value * position_size
    
    def validate_price_levels(self, entry: float, stop_loss: float, take_profit: float, min_step: float) -> Tuple[bool, str]:
        """
        Validate that price levels are properly spaced.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            min_step: Minimum price step
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check minimum distance from entry
        sl_distance = abs(entry - stop_loss)
        tp_distance = abs(take_profit - entry)
        
        min_distance = min_step * 5  # At least 5 ticks away
        
        if sl_distance < min_distance:
            return False, f"Stop loss too close to entry: {sl_distance} < {min_distance}"
        
        if tp_distance < min_distance:
            return False, f"Take profit too close to entry: {tp_distance} < {min_distance}"
        
        # Check that SL and TP are on opposite sides of entry
        if (stop_loss > entry) == (take_profit > entry):
            return False, "Stop loss and take profit must be on opposite sides of entry"
        
        return True, "Price levels valid"
    
    def calculate_risk_reward_ratio(self, entry: float, stop_loss: float, take_profit: float) -> float:
        """
        Calculate risk-reward ratio.
        
        Args:
            entry: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Risk-reward ratio
        """
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
    
    def calculate_position_value(self, price: float, size: float, point_value: float) -> float:
        """
        Calculate total position value.
        
        Args:
            price: Current price
            size: Position size
            point_value: Value per point
            
        Returns:
            Total position value
        """
        return price * size * point_value
    
    def calculate_margin_required(self, position_value: float, margin_requirement: float) -> float:
        """
        Calculate margin required for position.
        
        Args:
            position_value: Total position value
            margin_requirement: Margin requirement (as decimal)
            
        Returns:
            Required margin
        """
        return position_value * margin_requirement
    
    def calculate_leverage(self, position_value: float, margin_required: float) -> float:
        """
        Calculate leverage used.
        
        Args:
            position_value: Total position value
            margin_required: Required margin
            
        Returns:
            Leverage ratio
        """
        if margin_required == 0:
            return 0.0
        
        return position_value / margin_required


class FeesModel:
    """Model for trading costs and fees."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.spread = config.get('spread', 0.0001)  # Default spread
        self.commission = config.get('commission', 0.0)  # Commission per trade
        self.swap_rate = config.get('swap_rate', 0.0)  # Overnight swap rate
    
    def calculate_spread_cost(self, position_size: float, pip_value: float) -> float:
        """
        Calculate spread cost for a position.
        
        Args:
            position_size: Position size
            pip_value: Value per pip
            
        Returns:
            Spread cost
        """
        return self.spread * pip_value * position_size
    
    def calculate_commission_cost(self, position_value: float) -> float:
        """
        Calculate commission cost.
        
        Args:
            position_value: Position value
            
        Returns:
            Commission cost
        """
        return position_value * self.commission
    
    def calculate_swap_cost(self, position_value: float, days_held: int) -> float:
        """
        Calculate overnight swap cost.
        
        Args:
            position_value: Position value
            days_held: Number of days position is held
            
        Returns:
            Swap cost
        """
        return position_value * self.swap_rate * days_held
    
    def calculate_total_costs(self, position_size: float, position_value: float, pip_value: float, days_held: int = 1) -> float:
        """
        Calculate total trading costs.
        
        Args:
            position_size: Position size
            position_value: Position value
            pip_value: Value per pip
            days_held: Number of days position is held
            
        Returns:
            Total costs
        """
        spread_cost = self.calculate_spread_cost(position_size, pip_value)
        commission_cost = self.calculate_commission_cost(position_value)
        swap_cost = self.calculate_swap_cost(position_value, days_held)
        
        return spread_cost + commission_cost + swap_cost
    
    def calculate_net_pnl(self, gross_pnl: float, total_costs: float) -> float:
        """
        Calculate net P&L after costs.
        
        Args:
            gross_pnl: Gross P&L
            total_costs: Total trading costs
            
        Returns:
            Net P&L
        """
        return gross_pnl - total_costs
    
    def calculate_net_risk_reward(self, gross_rr: float, entry_costs: float, exit_costs: float, risk_amount: float) -> float:
        """
        Calculate net risk-reward ratio after costs.
        
        Args:
            gross_rr: Gross risk-reward ratio
            entry_costs: Entry costs
            exit_costs: Exit costs
            risk_amount: Risk amount
            
        Returns:
            Net risk-reward ratio
        """
        if risk_amount == 0:
            return 0.0
        
        total_costs = entry_costs + exit_costs
        net_reward = (gross_rr * risk_amount) - total_costs
        
        return net_reward / risk_amount if risk_amount > 0 else 0.0