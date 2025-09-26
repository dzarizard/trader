"""
Tests for pricing and rounding utilities.
"""
import pytest
import numpy as np
from app.pricing import PricingEngine, FeesModel


class TestPricingEngine:
    """Test pricing engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'fees': {
                'spread': 0.0001,
                'commission': 0.0001,
                'swap_rate': 0.0001
            }
        }
        self.pricing_engine = PricingEngine(self.config)
    
    def test_round_price_fx(self):
        """Test price rounding for FX instruments."""
        # Test EUR/USD with 4 decimal places
        price = 1.12345
        min_step = 0.0001
        rounded = self.pricing_engine.round_price(price, min_step)
        assert rounded == 1.1235
        
        # Test rounding down
        price = 1.12344
        rounded = self.pricing_engine.round_price(price, min_step)
        assert rounded == 1.1234
    
    def test_round_price_indices(self):
        """Test price rounding for index instruments."""
        # Test NAS100 with 1 decimal place
        price = 15000.67
        min_step = 1.0
        rounded = self.pricing_engine.round_price(price, min_step)
        assert rounded == 15001.0
        
        # Test rounding down
        price = 15000.4
        rounded = self.pricing_engine.round_price(price, min_step)
        assert rounded == 15000.0
    
    def test_round_size(self):
        """Test position size rounding."""
        # Test lot size rounding
        size = 0.123
        lot_step = 0.01
        rounded = self.pricing_engine.round_size(size, lot_step)
        assert rounded == 0.12
        
        # Test minimum size
        size = 0.005
        rounded = self.pricing_engine.round_size(size, lot_step)
        assert rounded == 0.01
    
    def test_calculate_pip_distance(self):
        """Test pip distance calculation."""
        entry = 1.1000
        exit = 1.1050
        min_step = 0.0001
        distance = self.pricing_engine.calculate_pip_distance(entry, exit, min_step)
        assert distance == 50.0  # 50 pips
    
    def test_calculate_pip_value(self):
        """Test pip value calculation."""
        pip_distance = 50.0
        pip_value = 10.0
        position_size = 1.0
        total_value = self.pricing_engine.calculate_pip_value(pip_distance, pip_value, position_size)
        assert total_value == 500.0
    
    def test_validate_price_levels_valid(self):
        """Test valid price level validation."""
        entry = 1.1000
        stop_loss = 1.0950
        take_profit = 1.1100
        min_step = 0.0001
        
        is_valid, reason = self.pricing_engine.validate_price_levels(entry, stop_loss, take_profit, min_step)
        assert is_valid
        assert reason == "Price levels valid"
    
    def test_validate_price_levels_invalid_sl_too_close(self):
        """Test invalid price levels - SL too close."""
        entry = 1.1000
        stop_loss = 1.0999  # Too close
        take_profit = 1.1100
        min_step = 0.0001
        
        is_valid, reason = self.pricing_engine.validate_price_levels(entry, stop_loss, take_profit, min_step)
        assert not is_valid
        assert "Stop loss too close" in reason
    
    def test_validate_price_levels_invalid_same_side(self):
        """Test invalid price levels - SL and TP on same side."""
        entry = 1.1000
        stop_loss = 1.0950
        take_profit = 1.0900  # Same side as SL
        min_step = 0.0001
        
        is_valid, reason = self.pricing_engine.validate_price_levels(entry, stop_loss, take_profit, min_step)
        assert not is_valid
        assert "opposite sides" in reason
    
    def test_calculate_risk_reward_ratio(self):
        """Test risk-reward ratio calculation."""
        entry = 1.1000
        stop_loss = 1.0950
        take_profit = 1.1100
        
        rr = self.pricing_engine.calculate_risk_reward_ratio(entry, stop_loss, take_profit)
        assert rr == 2.0  # 50 pips risk, 100 pips reward
    
    def test_calculate_position_value(self):
        """Test position value calculation."""
        price = 1.1000
        size = 1.0
        point_value = 10.0
        
        value = self.pricing_engine.calculate_position_value(price, size, point_value)
        assert value == 11.0
    
    def test_calculate_margin_required(self):
        """Test margin requirement calculation."""
        position_value = 10000.0
        margin_requirement = 0.01  # 1%
        
        margin = self.pricing_engine.calculate_margin_required(position_value, margin_requirement)
        assert margin == 100.0
    
    def test_calculate_leverage(self):
        """Test leverage calculation."""
        position_value = 10000.0
        margin_required = 100.0
        
        leverage = self.pricing_engine.calculate_leverage(position_value, margin_required)
        assert leverage == 100.0


class TestFeesModel:
    """Test fees model functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'spread': 0.0001,
            'commission': 0.0001,
            'swap_rate': 0.0001
        }
        self.fees_model = FeesModel(self.config)
    
    def test_calculate_spread_cost(self):
        """Test spread cost calculation."""
        position_size = 1.0
        pip_value = 10.0
        
        cost = self.fees_model.calculate_spread_cost(position_size, pip_value)
        assert cost == 1.0  # 0.0001 * 10 * 1.0
    
    def test_calculate_commission_cost(self):
        """Test commission cost calculation."""
        position_value = 10000.0
        
        cost = self.fees_model.calculate_commission_cost(position_value)
        assert cost == 1.0  # 10000 * 0.0001
    
    def test_calculate_swap_cost(self):
        """Test swap cost calculation."""
        position_value = 10000.0
        days_held = 1
        
        cost = self.fees_model.calculate_swap_cost(position_value, days_held)
        assert cost == 1.0  # 10000 * 0.0001 * 1
    
    def test_calculate_total_costs(self):
        """Test total costs calculation."""
        position_size = 1.0
        position_value = 10000.0
        pip_value = 10.0
        days_held = 1
        
        total_cost = self.fees_model.calculate_total_costs(position_size, position_value, pip_value, days_held)
        expected = 1.0 + 1.0 + 1.0  # spread + commission + swap
        assert total_cost == expected
    
    def test_calculate_net_pnl(self):
        """Test net P&L calculation."""
        gross_pnl = 100.0
        total_costs = 3.0
        
        net_pnl = self.fees_model.calculate_net_pnl(gross_pnl, total_costs)
        assert net_pnl == 97.0
    
    def test_calculate_net_risk_reward(self):
        """Test net risk-reward ratio calculation."""
        gross_rr = 2.0
        entry_costs = 1.0
        exit_costs = 1.0
        risk_amount = 50.0
        
        net_rr = self.fees_model.calculate_net_risk_reward(gross_rr, entry_costs, exit_costs, risk_amount)
        # Gross reward = 2.0 * 50 = 100, net reward = 100 - 2 = 98, net RR = 98/50 = 1.96
        assert abs(net_rr - 1.96) < 0.01
    
    def test_calculate_net_risk_reward_zero_risk(self):
        """Test net risk-reward with zero risk."""
        gross_rr = 2.0
        entry_costs = 1.0
        exit_costs = 1.0
        risk_amount = 0.0
        
        net_rr = self.fees_model.calculate_net_risk_reward(gross_rr, entry_costs, exit_costs, risk_amount)
        assert net_rr == 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {}
        self.pricing_engine = PricingEngine(self.config)
        self.fees_model = FeesModel(self.config)
    
    def test_round_price_invalid_step(self):
        """Test price rounding with invalid step size."""
        price = 1.1000
        min_step = 0.0  # Invalid
        
        rounded = self.pricing_engine.round_price(price, min_step)
        assert rounded == price  # Should return original price
    
    def test_round_size_invalid_step(self):
        """Test size rounding with invalid step size."""
        size = 1.0
        lot_step = -0.01  # Invalid
        
        rounded = self.pricing_engine.round_size(size, lot_step)
        assert rounded == size  # Should return original size
    
    def test_calculate_leverage_zero_margin(self):
        """Test leverage calculation with zero margin."""
        position_value = 10000.0
        margin_required = 0.0
        
        leverage = self.pricing_engine.calculate_leverage(position_value, margin_required)
        assert leverage == 0.0
    
    def test_fees_model_empty_config(self):
        """Test fees model with empty configuration."""
        config = {}
        fees_model = FeesModel(config)
        
        # Should use default values
        cost = fees_model.calculate_spread_cost(1.0, 10.0)
        assert cost == 0.001  # Default spread 0.0001 * 10 * 1.0