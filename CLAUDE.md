# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
```

### Running Analysis
- Option analysis: `python options/day_option_analysis.py`
- Backtesting: `python backtest/backtest.py`
- CTP trading: `python ctp/ctpbee_test.py`

## Project Architecture

This is a quantitative trading project focused on Chinese futures and options markets with three main components:

### Core Modules

**options/**
- Option pricing models using Black-Scholes and QuantLib
- Volatility analysis and surface calculations
- Greeks computation for risk management
- Implied volatility calculations
- Uses akshare for market data and QuantLib for financial calculations

**backtest/**
- Backtesting framework built on backtrader
- Various trading strategies (SMA, KDJ, custom indicators)
- Historical data analysis from Chinese exchanges
- Performance analysis and visualization

**ctp/**
- Live trading integration with CTP (China's futures trading platform)
- Uses ctpbee and pyctp for market connectivity
- Real-time strategy execution
- K-line data processing

**statistic/**
- Mathematical models for market analysis
- Distribution analysis and statistical tools
- Market structure analysis

### Data Structure

The `data/` directory contains historical market data from Chinese exchanges:
- **CZCE**: Zhengzhou Commodity Exchange
- **DCE**: Dalian Commodity Exchange  
- **SHFE**: Shanghai Futures Exchange
- **GFEX**: Guangzhou Futures Exchange

Data files follow naming pattern: `{EXCHANGE}_{YYYYMMDD}.xlsx`

### Key Dependencies

- **QuantLib**: Advanced financial calculations and option pricing
- **backtrader**: Backtesting framework
- **ctpbee/pyctp**: CTP trading platform integration
- **akshare**: Chinese financial data provider
- **pandas/numpy**: Data manipulation
- **matplotlib/mplfinance**: Visualization

### Trading Focus

Primary focus on Chinese commodity futures and options:
- Agricultural products (cotton, sugar, etc.)
- Metals (copper, silver, nickel)
- Industrial commodities
- Uses Chinese market conventions and trading hours

### File Encoding

Historical data files use GB2312 encoding (Chinese character set). When reading CSV/Excel files, use appropriate encoding parameters.