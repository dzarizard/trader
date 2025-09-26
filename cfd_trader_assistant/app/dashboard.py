"""
Streamlit dashboard for CFD Trader Assistant.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="CFD Trader Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .signal-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .long-signal {
        border-left: 4px solid #28a745;
    }
    .short-signal {
        border-left: 4px solid #dc3545;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


class DashboardData:
    """Data management for dashboard."""
    
    def __init__(self):
        self.load_configs()
        self.load_sample_data()
    
    def load_configs(self):
        """Load configuration files."""
        try:
            with open('config/instruments.yaml', 'r') as f:
                self.instruments_config = yaml.safe_load(f)
            
            with open('config/rules.yaml', 'r') as f:
                self.rules_config = yaml.safe_load(f)
            
            with open('config/account.yaml', 'r') as f:
                self.account_config = yaml.safe_load(f)
                
        except Exception as e:
            logger.error(f"Error loading configs: {e}")
            self.instruments_config = {}
            self.rules_config = {}
            self.account_config = {}
    
    def load_sample_data(self):
        """Load sample data for demonstration."""
        # Sample signals data
        self.sample_signals = [
            {
                'id': 'NAS100_LONG_20241201_143000',
                'timestamp': datetime.now() - timedelta(hours=2),
                'side': 'LONG',
                'symbol': 'NAS100',
                'entry_price': 18500.0,
                'stop_loss': 18450.0,
                'take_profit': 18600.0,
                'risk_reward_ratio': 2.0,
                'why': 'Trend(HTF) OK; Breakout(20); ATR 0.8%; Vol 1.3×; brak makro w 30m',
                'status': 'ACTIVE',
                'bars_since_entry': 5
            },
            {
                'id': 'EURUSD_SHORT_20241201_120000',
                'timestamp': datetime.now() - timedelta(hours=4),
                'side': 'SHORT',
                'symbol': 'EURUSD',
                'entry_price': 1.0850,
                'stop_loss': 1.0870,
                'take_profit': 1.0810,
                'risk_reward_ratio': 2.0,
                'why': 'Trend(HTF) OK; MACD Cross; ATR 0.5%; Vol 1.1×; brak makro w 30m',
                'status': 'ACTIVE',
                'bars_since_entry': 8
            },
            {
                'id': 'DAX40_LONG_20241130_160000',
                'timestamp': datetime.now() - timedelta(days=1, hours=2),
                'side': 'LONG',
                'symbol': 'DAX40',
                'entry_price': 18200.0,
                'stop_loss': 18150.0,
                'take_profit': 18300.0,
                'risk_reward_ratio': 2.0,
                'why': 'Trend(HTF) OK; ROC momentum; ATR 0.6%; Vol 1.5×; brak makro w 30m',
                'status': 'HIT_TP',
                'bars_since_entry': 12
            }
        ]
        
        # Sample performance data
        self.sample_performance = {
            'total_trades': 45,
            'winning_trades': 28,
            'losing_trades': 17,
            'win_rate': 62.2,
            'total_pnl': 1250.50,
            'max_drawdown': -320.75,
            'sharpe_ratio': 1.85,
            'profit_factor': 1.68,
            'avg_win': 85.30,
            'avg_loss': -45.20,
            'largest_win': 245.80,
            'largest_loss': -125.40
        }
        
        # Sample equity curve data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
        equity_values = [10000 + i * 25 + (i % 7 - 3) * 15 for i in range(len(dates))]
        self.equity_curve = pd.DataFrame({
            'date': dates,
            'equity': equity_values
        })


def render_header():
    """Render dashboard header."""
    st.markdown('<div class="main-header">📊 CFD Trader Assistant</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Account Equity", "$10,000", "2.5%")
    
    with col2:
        st.metric("Active Signals", "2", "1")
    
    with col3:
        st.metric("Daily P&L", "$125.50", "1.25%")


def render_signals_tab(data: DashboardData):
    """Render signals tab."""
    st.header("📈 Trading Signals")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        symbol_filter = st.selectbox(
            "Symbol",
            ["All"] + [instr['symbol'] for instr in data.instruments_config.get('instruments', [])]
        )
    
    with col2:
        side_filter = st.selectbox("Side", ["All", "LONG", "SHORT"])
    
    with col3:
        status_filter = st.selectbox("Status", ["All", "ACTIVE", "HIT_SL", "HIT_TP", "TIME_STOP", "TREND_BREAK"])
    
    with col4:
        time_filter = st.selectbox("Time Range", ["All", "Today", "This Week", "This Month"])
    
    # Filter signals
    filtered_signals = data.sample_signals.copy()
    
    if symbol_filter != "All":
        filtered_signals = [s for s in filtered_signals if s['symbol'] == symbol_filter]
    
    if side_filter != "All":
        filtered_signals = [s for s in filtered_signals if s['side'] == side_filter]
    
    if status_filter != "All":
        filtered_signals = [s for s in filtered_signals if s['status'] == status_filter]
    
    # Display signals
    if not filtered_signals:
        st.info("No signals found matching the selected filters.")
        return
    
    for signal in filtered_signals:
        signal_class = "long-signal" if signal['side'] == 'LONG' else "short-signal"
        
        with st.container():
            st.markdown(f'<div class="signal-card {signal_class}">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.write(f"**{signal['side']} {signal['symbol']}**")
                st.write(f"Entry: {signal['entry_price']:.4f}")
                st.write(f"Time: {signal['timestamp'].strftime('%H:%M:%S')}")
            
            with col2:
                st.write(f"**Stop Loss:** {signal['stop_loss']:.4f}")
                st.write(f"**Take Profit:** {signal['take_profit']:.4f}")
                st.write(f"**R:R:** {signal['risk_reward_ratio']:.1f}")
            
            with col3:
                status_color = {
                    'ACTIVE': '🟢',
                    'HIT_SL': '🔴',
                    'HIT_TP': '🟢',
                    'TIME_STOP': '🟡',
                    'TREND_BREAK': '🟡'
                }
                st.write(f"**Status:** {status_color.get(signal['status'], '⚪')} {signal['status']}")
                st.write(f"**Bars:** {signal['bars_since_entry']}")
            
            with col4:
                st.write(f"**Why:** {signal['why']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Signal statistics
    st.subheader("Signal Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    active_signals = [s for s in filtered_signals if s['status'] == 'ACTIVE']
    long_signals = [s for s in filtered_signals if s['side'] == 'LONG']
    short_signals = [s for s in filtered_signals if s['side'] == 'SHORT']
    
    with col1:
        st.metric("Active Signals", len(active_signals))
    
    with col2:
        st.metric("Long Signals", len(long_signals))
    
    with col3:
        st.metric("Short Signals", len(short_signals))
    
    with col4:
        avg_rr = sum(s['risk_reward_ratio'] for s in filtered_signals) / len(filtered_signals) if filtered_signals else 0
        st.metric("Avg R:R", f"{avg_rr:.1f}")


def render_charts_tab(data: DashboardData):
    """Render charts tab."""
    st.header("📊 Market Analysis")
    
    # Symbol selection
    symbols = [instr['symbol'] for instr in data.instruments_config.get('instruments', [])]
    selected_symbol = st.selectbox("Select Symbol", symbols, key="chart_symbol")
    
    if selected_symbol:
        # Generate sample OHLCV data
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='1H')
        np.random.seed(42)  # For reproducible data
        
        # Generate realistic price data
        base_price = 18500 if 'NAS' in selected_symbol else 1.0850 if 'EUR' in selected_symbol else 18200
        returns = np.random.normal(0, 0.001, len(dates))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        ohlcv_data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            volume = np.random.randint(1000, 10000)
            
            ohlcv_data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(ohlcv_data)
        
        # Create candlestick chart
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f'{selected_symbol} Price Chart', 'Volume'),
            row_width=[0.7, 0.3]
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=selected_symbol
            ),
            row=1, col=1
        )
        
        # Add moving averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_20'], name='SMA 20', line=dict(color='orange', width=1)),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_50'], name='SMA 50', line=dict(color='blue', width=1)),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_200'], name='SMA 200', line=dict(color='red', width=1)),
            row=1, col=1
        )
        
        # Volume chart
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color='lightblue'),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=f'{selected_symbol} Technical Analysis',
            xaxis_rangeslider_visible=False,
            height=600,
            showlegend=True
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Technical indicators
        st.subheader("Technical Indicators")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            current_price = df['close'].iloc[-1]
            sma_20 = df['SMA_20'].iloc[-1]
            sma_50 = df['SMA_50'].iloc[-1]
            sma_200 = df['SMA_200'].iloc[-1]
            
            st.metric("Current Price", f"{current_price:.4f}")
            st.metric("SMA 20", f"{sma_20:.4f}")
            st.metric("SMA 50", f"{sma_50:.4f}")
            st.metric("SMA 200", f"{sma_200:.4f}")
        
        with col2:
            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Calculate ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=14).mean()
            
            st.metric("RSI (14)", f"{rsi.iloc[-1]:.2f}")
            st.metric("ATR (14)", f"{atr.iloc[-1]:.4f}")
        
        with col3:
            # Calculate MACD
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            st.metric("MACD", f"{macd.iloc[-1]:.4f}")
            st.metric("MACD Signal", f"{signal.iloc[-1]:.4f}")
            st.metric("MACD Histogram", f"{histogram.iloc[-1]:.4f}")


def render_performance_tab(data: DashboardData):
    """Render performance tab."""
    st.header("📈 Performance Analytics")
    
    # Performance metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", data.sample_performance['total_trades'])
        st.metric("Win Rate", f"{data.sample_performance['win_rate']:.1f}%")
        st.metric("Profit Factor", f"{data.sample_performance['profit_factor']:.2f}")
    
    with col2:
        st.metric("Total P&L", f"${data.sample_performance['total_pnl']:.2f}")
        st.metric("Max Drawdown", f"${data.sample_performance['max_drawdown']:.2f}")
        st.metric("Sharpe Ratio", f"{data.sample_performance['sharpe_ratio']:.2f}")
    
    with col3:
        st.metric("Avg Win", f"${data.sample_performance['avg_win']:.2f}")
        st.metric("Avg Loss", f"${data.sample_performance['avg_loss']:.2f}")
        st.metric("Largest Win", f"${data.sample_performance['largest_win']:.2f}")
    
    with col4:
        st.metric("Largest Loss", f"${data.sample_performance['largest_loss']:.2f}")
        st.metric("Winning Trades", data.sample_performance['winning_trades'])
        st.metric("Losing Trades", data.sample_performance['losing_trades'])
    
    # Equity curve
    st.subheader("Equity Curve")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.equity_curve['date'],
        y=data.equity_curve['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='blue', width=2)
    ))
    
    fig.update_layout(
        title="Account Equity Over Time",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Performance by symbol
    st.subheader("Performance by Symbol")
    
    symbol_performance = pd.DataFrame({
        'Symbol': ['NAS100', 'EURUSD', 'DAX40', 'SPX500', 'GBPUSD'],
        'Trades': [15, 12, 8, 6, 4],
        'Win Rate': [65.0, 58.3, 75.0, 66.7, 50.0],
        'P&L': [450.25, 320.50, 280.75, 150.00, -50.00]
    })
    
    fig = px.bar(symbol_performance, x='Symbol', y='P&L', 
                 title="P&L by Symbol", color='P&L',
                 color_continuous_scale=['red', 'green'])
    st.plotly_chart(fig, use_container_width=True)
    
    # Monthly performance
    st.subheader("Monthly Performance")
    
    monthly_data = pd.DataFrame({
        'Month': ['Oct 2024', 'Nov 2024', 'Dec 2024'],
        'P&L': [320.50, 580.25, 349.75],
        'Trades': [12, 18, 15]
    })
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(x=monthly_data['Month'], y=monthly_data['P&L'], name="P&L", marker_color='lightblue'),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=monthly_data['Month'], y=monthly_data['Trades'], name="Trades", line=dict(color='red')),
        secondary_y=True,
    )
    
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="P&L ($)", secondary_y=False)
    fig.update_yaxes(title_text="Number of Trades", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)


def render_settings_tab(data: DashboardData):
    """Render settings tab."""
    st.header("⚙️ Settings")
    
    # Configuration display (read-only)
    st.subheader("Trading Rules")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Trend Settings**")
        trend_config = data.rules_config.get('trend', {})
        st.json(trend_config)
        
        st.write("**Entry Settings**")
        entry_config = data.rules_config.get('entry', {})
        st.json(entry_config)
    
    with col2:
        st.write("**Quality Settings**")
        quality_config = data.rules_config.get('quality', {})
        st.json(quality_config)
        
        st.write("**Risk Settings**")
        risk_config = data.rules_config.get('risk', {})
        st.json(risk_config)
    
    # Account settings
    st.subheader("Account Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Account Configuration**")
        account_config = data.account_config
        st.json(account_config)
    
    with col2:
        st.write("**Instruments**")
        instruments = data.instruments_config.get('instruments', [])
        st.write(f"Total instruments: {len(instruments)}")
        
        for instr in instruments[:5]:  # Show first 5
            st.write(f"- {instr['symbol']} ({instr['kind']})")
        
        if len(instruments) > 5:
            st.write(f"... and {len(instruments) - 5} more")
    
    # Alert settings
    st.subheader("Alert Settings")
    
    alert_status = {
        'telegram': {'enabled': True, 'configured': True},
        'slack': {'enabled': False, 'configured': False},
        'email': {'enabled': False, 'configured': False}
    }
    
    for channel, status in alert_status.items():
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{channel.title()}**")
        with col2:
            if status['enabled'] and status['configured']:
                st.success("✅ Enabled & Configured")
            elif status['enabled']:
                st.warning("⚠️ Enabled but not configured")
            else:
                st.info("ℹ️ Disabled")
    
    # System status
    st.subheader("System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Data Providers", "2 Active", "Yahoo, Stooq")
    
    with col2:
        st.metric("Last Update", "2 min ago", "🟢 Online")
    
    with col3:
        st.metric("System Health", "Good", "🟢")


def main():
    """Main dashboard function."""
    # Initialize data
    data = DashboardData()
    
    # Sidebar
    st.sidebar.title("Navigation")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Select Page",
        ["Signals", "Charts", "Performance", "Settings"]
    )
    
    # System info in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Info")
    st.sidebar.metric("Uptime", "2h 15m")
    st.sidebar.metric("Memory Usage", "45%")
    st.sidebar.metric("CPU Usage", "12%")
    
    # Alert status
    st.sidebar.markdown("### Alert Status")
    st.sidebar.success("🟢 Telegram: Active")
    st.sidebar.info("⚪ Slack: Disabled")
    st.sidebar.info("⚪ Email: Disabled")
    
    # Main content
    if page == "Signals":
        render_header()
        render_signals_tab(data)
    elif page == "Charts":
        render_header()
        render_charts_tab(data)
    elif page == "Performance":
        render_header()
        render_performance_tab(data)
    elif page == "Settings":
        render_header()
        render_settings_tab(data)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>CFD Trader Assistant v1.0 | 
            <strong>⚠️ WARNING:</strong> This is not investment advice. CFD trading involves high risk.</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()