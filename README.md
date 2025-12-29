# Python Trade View - 策略隔离交易系统

> 基于策略隔离架构的量化交易回测与实盘监控系统

## 项目定位

本项目采用**策略隔离架构**，将每个交易策略作为独立的代码模块进行管理和测试。

### 核心理念

- **策略隔离**: 每个策略文件独立存在，互不干扰
- **灵活组合**: 任意策略 + 任意股票数据 = 独立回测结果
- **双轨运行**: 回测系统验证策略，监控系统执行交易

## 系统架构

```
PythonTradeView/
├── strategies/              # 策略库（每个文件一个策略）
│   ├── __init__.py
│   ├── strategy_template.py # 策略模板
│   └── ...                  # 用户自定义策略
│
├── backtester/              # 回测系统
│   ├── engine.py            # 回测引擎
│   ├── data/                # 数据目录
│   └── requirements.txt
│
├── server_trader/           # 实盘监控系统
│   ├── src/
│   │   ├── main.py          # 主程序
│   │   ├── trader_engine.py # 交易引擎
│   │   ├── data_fetcher.py  # 数据获取
│   │   └── alerter.py       # 告警系统
│   ├── config_template.json
│   └── requirements.txt
│
├── configs/                 # 配置文件
│   └── _default.json        # 默认配置模板
│
└── docker-compose.yml       # Docker部署配置
```

## 核心概念

### 1. 策略隔离

每个策略是一个独立的 Python 文件，实现统一的策略接口：

```python
class Strategy:
    def __init__(self, params):
        """初始化策略"""
        pass

    def next(self, data):
        """处理每个K线"""
        pass

    def should_buy(self):
        """买入信号"""
        pass

    def should_sell(self):
        """卖出信号"""
        pass
```

### 2. 灵活组合

- **旧逻辑**: 单一策略 + 本地参数遍历测试
- **新逻辑**: 多策略 + 多股票 + 独立回测

| 维度     | 旧架构       | 新架构            |
| -------- | ------------ | ----------------- |
| 策略管理 | 单一策略文件 | 多策略文件隔离    |
| 参数优化 | 本地参数遍历 | 策略级别独立优化  |
| 测试方式 | 参数组合测试 | 策略-股票组合测试 |
| 扩展性   | 修改原策略   | 新增策略文件      |

### 3. 双系统架构

#### 回测系统 (backtester/)

- 策略验证和回测
- 历史数据测试
- 性能指标计算

#### 监控系统 (server_trader/)

- 实时行情监控
- 信号触发和告警
- 实盘交易执行（可选）

## 技术栈

- **语言**: Python 3.8+
- **回测**: Backtrader
- **数据**: yfinance / Longport API
- **监控**: APScheduler
- **告警**: Telegram Bot
- **部署**: Docker

## 许可证

MIT License

---

**注意**: 本项目是 Vibe Coding 迭代后的超级大粪坑，不构成任何投资建议。实盘交易有风险，投资需谨慎。
