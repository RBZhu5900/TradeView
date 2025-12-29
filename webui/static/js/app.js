/**
 * PythonTradeView - 策略回测系统前端
 */

// ============= 全局状态 =============
const state = {
    strategies: [],
    symbols: [],
    configs: [],
    currentStrategy: null,
    currentConfigId: null,
    chart: null,
    isLoading: false
};

// ============= API 接口 =============
const API = {
    async getStrategies() {
        const res = await fetch('/api/strategies');
        return res.json();
    },
    
    async getSymbols() {
        const res = await fetch('/api/symbols');
        return res.json();
    },
    
    async getLocalSymbols() {
        const res = await fetch('/api/symbols/local');
        return res.json();
    },
    
    async addSymbol(symbol, startDate, endDate) {
        const res = await fetch('/api/symbols/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                start_date: startDate,
                end_date: endDate
            })
        });
        return res.json();
    },
    
    async getStrategyDetail(strategyName) {
        const res = await fetch(`/api/strategy/${strategyName}`);
        return res.json();
    },
    
    async runBacktest(params) {
        const res = await fetch('/api/backtest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        return res.json();
    },
    
    // 配置管理 API
    async getConfigs(strategy = null) {
        let url = '/api/configs';
        if (strategy) {
            url += `?strategy=${encodeURIComponent(strategy)}`;
        }
        const res = await fetch(url);
        return res.json();
    },
    
    async getConfig(configId) {
        const res = await fetch(`/api/configs/${configId}`);
        return res.json();
    },
    
    async saveConfig(data) {
        const res = await fetch('/api/configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },
    
    async deleteConfig(configId) {
        const res = await fetch(`/api/configs/${configId}`, {
            method: 'DELETE'
        });
        return res.json();
    },
    
    async exportConfig(configId) {
        const res = await fetch(`/api/configs/${configId}/export`);
        return res.json();
    },
    
    async importConfig(jsonData) {
        const res = await fetch('/api/configs/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ json_data: jsonData })
        });
        return res.json();
    }
};

// ============= DOM 元素 =============
const elements = {
    strategySelect: document.getElementById('strategy-select'),
    symbolSelect: document.getElementById('symbol-select'),
    configSelect: document.getElementById('config-select'),
    deleteConfigBtn: document.getElementById('delete-config-btn'),
    startDate: document.getElementById('start-date'),
    endDate: document.getElementById('end-date'),
    initialCapital: document.getElementById('initial-capital'),
    runBacktestBtn: document.getElementById('run-backtest'),
    saveConfigBtn: document.getElementById('save-config-btn'),
    paramsContainer: document.getElementById('params-container'),
    paramsFields: document.getElementById('params-fields'),
    loadingOverlay: document.getElementById('loading-overlay'),
    chartPlaceholder: document.getElementById('chart-placeholder'),
    tradesList: document.getElementById('trades-list'),
    tradeCount: document.getElementById('trade-count'),
    toastContainer: document.getElementById('toast-container'),
    statusBadge: document.getElementById('status-badge'),
    // 模态框元素
    saveConfigModal: document.getElementById('save-config-modal'),
    configName: document.getElementById('config-name'),
    configDescription: document.getElementById('config-description'),
    configBindSymbol: document.getElementById('config-bind-symbol'),
    closeModalBtn: document.getElementById('close-modal-btn'),
    cancelSaveBtn: document.getElementById('cancel-save-btn'),
    confirmSaveBtn: document.getElementById('confirm-save-btn'),
    // 指标元素
    metricReturn: document.getElementById('metric-return'),
    metricAnnual: document.getElementById('metric-annual'),
    metricDrawdown: document.getElementById('metric-drawdown'),
    metricSharpe: document.getElementById('metric-sharpe'),
    metricWinrate: document.getElementById('metric-winrate'),
    metricProfitFactor: document.getElementById('metric-profit-factor')
};

// ============= 初始化 =============
async function init() {
    try {
        // 设置默认日期
        const today = new Date();
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(today.getFullYear() - 1);
        
        elements.endDate.value = formatDate(today);
        elements.startDate.value = formatDate(oneYearAgo);
        
        // 加载策略和股票列表
        await Promise.all([
            loadStrategies(),
            loadSymbols()
        ]);
        
        // 绑定事件
        bindEvents();
        
        showToast('系统就绪', 'success');
    } catch (error) {
        console.error('初始化失败:', error);
        showToast('初始化失败: ' + error.message, 'error');
    }
}

// 加载策略列表
async function loadStrategies() {
    const result = await API.getStrategies();
    
    if (result.success && result.data.length > 0) {
        state.strategies = result.data;
        
        elements.strategySelect.innerHTML = result.data.map(s => 
            `<option value="${s.module}">${s.name || s.module}</option>`
        ).join('');
        
        // 加载第一个策略的详情和配置
        await loadStrategyParams(result.data[0].module);
        await loadConfigs(result.data[0].module);
    } else {
        elements.strategySelect.innerHTML = '<option value="">无可用策略</option>';
    }
}

// 加载股票列表
async function loadSymbols() {
    const result = await API.getSymbols();
    
    if (result.success && result.data.length > 0) {
        state.symbols = result.data;
        
        // 添加一个"添加新股票"选项
        let options = result.data.map(s => 
            `<option value="${s}">${s}</option>`
        ).join('');
        options += '<option value="__ADD_NEW__">+ 添加新股票...</option>';
        
        elements.symbolSelect.innerHTML = options;
    } else {
        elements.symbolSelect.innerHTML = `
            <option value="">无本地数据</option>
            <option value="__ADD_NEW__">+ 添加新股票...</option>
        `;
    }
}

// 加载策略参数
async function loadStrategyParams(strategyName) {
    try {
        const result = await API.getStrategyDetail(strategyName);
        
        if (result.success && result.data.parameters) {
            state.currentStrategy = result.data;
            renderParams(result.data.parameters);
            elements.paramsContainer.style.display = 'block';
        } else {
            elements.paramsContainer.style.display = 'none';
        }
    } catch (error) {
        console.error('加载策略参数失败:', error);
        elements.paramsContainer.style.display = 'none';
    }
}

// 加载配置列表
async function loadConfigs(strategyName) {
    try {
        const result = await API.getConfigs(strategyName);
        
        if (result.success) {
            state.configs = result.data;
            renderConfigSelect(result.data);
        } else {
            state.configs = [];
            renderConfigSelect([]);
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        state.configs = [];
        renderConfigSelect([]);
    }
}

// 渲染配置选择器
function renderConfigSelect(configs) {
    let options = '<option value="">使用默认参数</option>';
    
    configs.forEach(config => {
        const symbol = config.symbol ? ` (${config.symbol})` : '';
        options += `<option value="${config.id}">${config.name}${symbol}</option>`;
    });
    
    elements.configSelect.innerHTML = options;
    state.currentConfigId = null;
    elements.deleteConfigBtn.style.display = 'none';
}

// 渲染参数字段
function renderParams(parameters, values = {}) {
    const html = Object.entries(parameters).map(([key, config]) => {
        const value = values[key] !== undefined ? values[key] : config.default;
        let inputHtml = '';
        
        if (config.options) {
            // 下拉选择
            inputHtml = `
                <select class="param-input" data-param="${key}">
                    ${config.options.map(opt => 
                        `<option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>`
                    ).join('')}
                </select>
            `;
        } else if (config.type === 'int' || config.type === 'float') {
            // 数字输入
            inputHtml = `
                <input type="number" 
                       class="param-input" 
                       data-param="${key}"
                       value="${value}"
                       ${config.min !== undefined ? `min="${config.min}"` : ''}
                       ${config.max !== undefined ? `max="${config.max}"` : ''}
                       ${config.type === 'float' ? 'step="0.1"' : ''}>
            `;
        } else {
            // 文本输入
            inputHtml = `
                <input type="text" 
                       class="param-input" 
                       data-param="${key}"
                       value="${value}">
            `;
        }
        
        return `
            <div class="param-field">
                <label class="param-label">${config.description || key}</label>
                ${inputHtml}
            </div>
        `;
    }).join('');
    
    elements.paramsFields.innerHTML = html;
}

// 获取当前参数值
function getParams() {
    const params = {};
    const inputs = elements.paramsFields.querySelectorAll('.param-input');
    
    inputs.forEach(input => {
        const key = input.dataset.param;
        let value = input.value;
        
        // 类型转换
        if (input.type === 'number') {
            value = input.step === '0.1' ? parseFloat(value) : parseInt(value);
        }
        
        params[key] = value;
    });
    
    return params;
}

// ============= 事件绑定 =============
function bindEvents() {
    // 策略选择变化
    elements.strategySelect.addEventListener('change', async (e) => {
        if (e.target.value) {
            await loadStrategyParams(e.target.value);
            await loadConfigs(e.target.value);
        }
    });
    
    // 配置选择变化
    elements.configSelect.addEventListener('change', async (e) => {
        const configId = e.target.value;
        
        if (configId) {
            await loadConfig(configId);
            state.currentConfigId = configId;
            elements.deleteConfigBtn.style.display = 'flex';
        } else {
            // 重置为默认参数
            if (state.currentStrategy && state.currentStrategy.parameters) {
                renderParams(state.currentStrategy.parameters);
            }
            state.currentConfigId = null;
            elements.deleteConfigBtn.style.display = 'none';
        }
    });
    
    // 删除配置按钮
    elements.deleteConfigBtn.addEventListener('click', async () => {
        if (state.currentConfigId && confirm('确定要删除这个配置吗？')) {
            await deleteConfig(state.currentConfigId);
        }
    });
    
    // 股票选择变化
    elements.symbolSelect.addEventListener('change', async (e) => {
        if (e.target.value === '__ADD_NEW__') {
            await showAddSymbolDialog();
            // 重置选择
            if (state.symbols.length > 0) {
                elements.symbolSelect.value = state.symbols[0];
            }
        }
    });
    
    // 运行回测
    elements.runBacktestBtn.addEventListener('click', runBacktest);
    
    // 保存配置按钮
    elements.saveConfigBtn.addEventListener('click', () => {
        openSaveConfigModal();
    });
    
    // 模态框事件
    elements.closeModalBtn.addEventListener('click', closeSaveConfigModal);
    elements.cancelSaveBtn.addEventListener('click', closeSaveConfigModal);
    elements.confirmSaveBtn.addEventListener('click', saveConfig);
    
    // 点击遮罩关闭模态框
    elements.saveConfigModal.addEventListener('click', (e) => {
        if (e.target === elements.saveConfigModal) {
            closeSaveConfigModal();
        }
    });
}

// 加载配置
async function loadConfig(configId) {
    try {
        const result = await API.getConfig(configId);
        
        if (result.success && result.data) {
            const config = result.data;
            
            // 应用参数到表单
            if (state.currentStrategy && state.currentStrategy.parameters) {
                renderParams(state.currentStrategy.parameters, config.params);
            }
            
            // 如果配置绑定了股票，自动选中
            if (config.symbol && state.symbols.includes(config.symbol)) {
                elements.symbolSelect.value = config.symbol;
            }
            
            showToast(`已加载配置: ${config.name}`, 'success');
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        showToast('加载配置失败', 'error');
    }
}

// 删除配置
async function deleteConfig(configId) {
    try {
        const result = await API.deleteConfig(configId);
        
        if (result.success) {
            showToast('配置已删除', 'success');
            // 重新加载配置列表
            const strategy = elements.strategySelect.value;
            await loadConfigs(strategy);
            // 重置参数为默认值
            if (state.currentStrategy && state.currentStrategy.parameters) {
                renderParams(state.currentStrategy.parameters);
            }
        } else {
            showToast(result.message || '删除失败', 'error');
        }
    } catch (error) {
        console.error('删除配置失败:', error);
        showToast('删除配置失败', 'error');
    }
}

// 打开保存配置模态框
function openSaveConfigModal() {
    const strategy = elements.strategySelect.value;
    const symbol = elements.symbolSelect.value;
    
    if (!strategy) {
        showToast('请先选择策略', 'error');
        return;
    }
    
    // 预填充名称
    const strategyName = state.currentStrategy?.name || strategy;
    const symbolPart = symbol && symbol !== '__ADD_NEW__' ? ` - ${symbol}` : '';
    elements.configName.value = `${strategyName}${symbolPart}`;
    elements.configDescription.value = '';
    elements.configBindSymbol.checked = !!symbol && symbol !== '__ADD_NEW__';
    
    elements.saveConfigModal.classList.add('active');
}

// 关闭保存配置模态框
function closeSaveConfigModal() {
    elements.saveConfigModal.classList.remove('active');
}

// 保存配置
async function saveConfig() {
    const strategy = elements.strategySelect.value;
    const name = elements.configName.value.trim();
    
    if (!name) {
        showToast('请输入配置名称', 'error');
        return;
    }
    
    const params = getParams();
    const symbol = elements.configBindSymbol.checked ? 
        (elements.symbolSelect.value !== '__ADD_NEW__' ? elements.symbolSelect.value : null) : 
        null;
    
    try {
        const result = await API.saveConfig({
            strategy: strategy,
            params: params,
            name: name,
            symbol: symbol,
            description: elements.configDescription.value.trim() || null,
            config_id: state.currentConfigId  // 如果有当前配置ID，则更新
        });
        
        if (result.success) {
            showToast('配置已保存', 'success');
            closeSaveConfigModal();
            // 重新加载配置列表
            await loadConfigs(strategy);
            // 选中新保存的配置
            if (result.data && result.data.id) {
                elements.configSelect.value = result.data.id;
                state.currentConfigId = result.data.id;
                elements.deleteConfigBtn.style.display = 'flex';
            }
        } else {
            showToast(result.message || '保存失败', 'error');
        }
    } catch (error) {
        console.error('保存配置失败:', error);
        showToast('保存配置失败', 'error');
    }
}

// 显示添加股票对话框
async function showAddSymbolDialog() {
    const symbol = prompt('请输入股票代码（如 AAPL, TSLA, MSFT）:');
    
    if (!symbol) return;
    
    setLoading(true);
    showToast(`正在下载 ${symbol.toUpperCase()} 数据...`, 'success');
    
    try {
        const result = await API.addSymbol(
            symbol.toUpperCase(),
            elements.startDate.value,
            elements.endDate.value
        );
        
        if (result.success) {
            showToast(result.message, 'success');
            // 重新加载股票列表
            await loadSymbols();
            // 选中新添加的股票
            elements.symbolSelect.value = symbol.toUpperCase();
        } else {
            showToast(result.message || '下载失败', 'error');
        }
    } catch (error) {
        showToast('添加股票失败: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

// 运行回测
async function runBacktest() {
    const strategy = elements.strategySelect.value;
    let symbol = elements.symbolSelect.value;
    
    if (!strategy) {
        showToast('请选择策略', 'error');
        return;
    }
    
    if (!symbol || symbol === '__ADD_NEW__') {
        showToast('请选择股票', 'error');
        return;
    }
    
    setLoading(true);
    
    try {
        const params = {
            strategy: strategy,
            symbol: symbol,
            start_date: elements.startDate.value || null,
            end_date: elements.endDate.value || null,
            initial_capital: parseFloat(elements.initialCapital.value) || 100000,
            params: getParams()
        };
        
        const result = await API.runBacktest(params);
        
        if (result.success) {
            updateMetrics(result.data);
            updateChart(result.data.equity_curve);
            updateTrades(result.data.trades);
            showToast('回测完成', 'success');
            
            // 更新股票列表（可能有新下载的数据）
            await loadSymbols();
            elements.symbolSelect.value = symbol;
        } else {
            showToast(result.message || '回测失败', 'error');
        }
    } catch (error) {
        console.error('回测错误:', error);
        showToast('回测执行失败: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

// ============= UI 更新 =============

// 更新指标显示
function updateMetrics(data) {
    const setValue = (el, value, suffix = '', isPercent = true) => {
        if (value === undefined || value === null || value === '--') {
            el.textContent = '--';
            el.className = 'metric-value';
            return;
        }
        
        const numValue = parseFloat(value);
        el.textContent = (numValue >= 0 && isPercent ? '+' : '') + value + suffix;
        
        // 设置颜色类
        if (isPercent) {
            el.className = 'metric-value ' + (numValue >= 0 ? 'positive' : 'negative');
        } else {
            el.className = 'metric-value';
        }
    };
    
    setValue(elements.metricReturn, data.return_pct, '%');
    setValue(elements.metricAnnual, data.annual_return_pct, '%');
    setValue(elements.metricDrawdown, -Math.abs(data.max_drawdown_pct), '%');
    setValue(elements.metricSharpe, data.sharpe_ratio, '', false);
    setValue(elements.metricWinrate, data.win_rate, '%', false);
    setValue(elements.metricProfitFactor, data.profit_factor, '', false);
}

// 更新权益曲线图表
function updateChart(equityCurve) {
    if (!equityCurve || equityCurve.length === 0) {
        elements.chartPlaceholder.classList.remove('hidden');
        return;
    }
    
    elements.chartPlaceholder.classList.add('hidden');
    
    const ctx = document.getElementById('equity-chart').getContext('2d');
    
    // 销毁旧图表
    if (state.chart) {
        state.chart.destroy();
    }
    
    // 准备数据
    const labels = equityCurve.map(e => new Date(e.datetime));
    const values = equityCurve.map(e => e.value);
    
    // 创建渐变
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 212, 170, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 212, 170, 0)');
    
    // 创建新图表
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '账户权益',
                data: values,
                borderColor: '#00d4aa',
                backgroundColor: gradient,
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: '#00d4aa',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(13, 17, 23, 0.95)',
                    titleColor: '#f0f6fc',
                    bodyColor: '#8b949e',
                    borderColor: '#30363d',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        title: function(context) {
                            const date = context[0].label;
                            return new Date(date).toLocaleDateString('zh-CN');
                        },
                        label: function(context) {
                            return '权益: $' + context.parsed.y.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            });
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'yyyy-MM'
                        }
                    },
                    grid: {
                        color: 'rgba(48, 54, 61, 0.5)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#8b949e',
                        maxRotation: 0
                    }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: 'rgba(48, 54, 61, 0.5)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#8b949e',
                        callback: function(value) {
                            return '$' + value.toLocaleString('en-US');
                        }
                    }
                }
            }
        }
    });
}

// 更新交易记录
function updateTrades(trades) {
    if (!trades || trades.length === 0) {
        elements.tradesList.innerHTML = `
            <div class="trades-empty">
                <div class="empty-icon">📝</div>
                <div class="empty-text">暂无交易记录</div>
            </div>
        `;
        elements.tradeCount.textContent = '0 笔';
        return;
    }
    
    elements.tradeCount.textContent = `${trades.length} 笔`;
    
    const html = trades.map(trade => {
        const isBuy = trade.type === 'BUY';
        const date = new Date(trade.datetime);
        const dateStr = date.toLocaleDateString('zh-CN');
        
        return `
            <div class="trade-item">
                <div class="trade-icon ${isBuy ? 'buy' : 'sell'}">
                    ${isBuy ? '买' : '卖'}
                </div>
                <div class="trade-info">
                    <div class="trade-type ${isBuy ? 'buy' : 'sell'}">
                        ${isBuy ? '买入' : '卖出'}
                    </div>
                    <div class="trade-date">${dateStr}</div>
                </div>
                <div class="trade-price">
                    <div class="trade-price-value">$${trade.price.toFixed(2)}</div>
                    <div class="trade-size">${trade.size.toFixed(2)} 股</div>
                </div>
            </div>
        `;
    }).join('');
    
    elements.tradesList.innerHTML = html;
}

// ============= 工具函数 =============

// 设置加载状态
function setLoading(loading) {
    state.isLoading = loading;
    elements.loadingOverlay.classList.toggle('active', loading);
    elements.runBacktestBtn.disabled = loading;
    
    // 更新状态标识
    const badge = elements.statusBadge;
    if (loading) {
        badge.innerHTML = '<span class="status-dot" style="background: #f59e0b; box-shadow: 0 0 8px #f59e0b; animation: none;"></span>运行中';
    } else {
        badge.innerHTML = '<span class="status-dot"></span>就绪';
    }
}

// 格式化日期
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// 显示 Toast 通知
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'success' ? '✓' : '✕'}</span>
        <span class="toast-message">${message}</span>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============= 启动应用 =============
document.addEventListener('DOMContentLoaded', init);
