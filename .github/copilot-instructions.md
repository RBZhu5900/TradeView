# AI Agent Instructions for PythonTradeView

## Project Overview

PythonTradeView is a stock trading automation system with two main components:

- `server_trader/`: A 24/7 alerting service that runs in Docker
- `backtester/`: A local backtesting tool using the `backtrader` framework
- `common_strategies/`: Shared strategy code used by both components

## Key Architecture Patterns

### Service Architecture

- Server uses a polling architecture (`server_trader/src/main.py`) with configurable intervals
- Strategies are instantiated per symbol to maintain state (`server_trader/src/trader_engine.py`)
- Data flow: `data_fetcher` → `trader_engine` → `alerter`

### Strategy Implementation

- All strategies should follow the interface in `common_strategies/src/strategies/`
- Strategy patterns defined in `Strategy.md`:
  - TIER 1: Trend confirmation (EMA, MACD)
  - TIER 2: Entry timing (multiple approaches with configurable parameters)

## Development Workflows

### Local Development

```bash
# Backtester setup
pip install -r backtester/requirements.txt
# Place data in backtester/data/
python backtester/run_backtest.py

# Server development
cp server_trader/.env.example server_trader/.env
# Edit .env with API credentials
docker compose up --build
```

### Configuration

- Strategy parameters in `configs/*.json`
- Default values in `configs/_default.json`
- Stock-specific overrides in `configs/AAPL.json` etc.

## Common Tasks

### Adding New Strategies

1. Create new file in `common_strategies/src/strategies/`
2. Follow pattern in `detailed_strategy.py`
3. Register in `trader_engine.py` WATCHLIST

### Configuring Alerts

- Edit alerter.py for new notification channels
- Alert format: "股票: {symbol}\n 信号: {signal}\n 价格: {price}"

### Adding Test Data

- Place CSV files in `backtester/data/`
- Format: OHLCV columns with datetime index
- See `sample_data.csv` for example

## Key Dependencies

- `backtrader`: Backtesting engine
- `apscheduler`: Task scheduling
- `pandas`, `yfinance`: Data handling
- Docker for deployment
