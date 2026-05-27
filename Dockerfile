FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libgtk-3-0 \
    libgbm-dev \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY main.py .
COPY src/ ./src/
COPY config/ ./config/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装Playwright浏览器
RUN playwright install chromium

# 创建日志和统计目录
RUN mkdir -p logs stats

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true

# 启动命令
CMD ["python", "main.py", "--continuous"]
