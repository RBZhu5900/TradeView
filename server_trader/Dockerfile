# 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY server_trader/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制共享策略代码和应用源代码
# 注意: docker-compose.yml 需要设置 build.context 为项目根目录
COPY common_strategies/src/ /app/common_strategies/
COPY server_trader/src/ /app/src/

# 创建日志目录
RUN mkdir -p /app/logs

# 设置Python环境变量，以便能找到共享模块
ENV PYTHONPATH="/app:${PYTHONPATH}"

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ps aux | grep -v grep | grep -q "python.*main.py" || exit 1

# 启动命令
CMD ["python", "-u", "src/main.py"]
