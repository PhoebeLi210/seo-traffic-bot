# 宝塔面板部署指南

本文档详细介绍如何在阿里云宝塔面板上部署SEO Traffic Bot。

## 📋 前置要求

- 阿里云ECS服务器（建议2核4G以上）
- 已安装宝塔面板（推荐7.9+版本）
- Python 3.8+ 环境
- 开放端口：8080（统计仪表盘）、5010（代理池，可选）

## 🚀 部署步骤

### 方式一：使用宝塔Python项目管理器（推荐）

#### 1. 上传代码到服务器

```bash
# 在服务器上执行
mkdir -p /www/wwwroot/seo-traffic-bot
cd /www/wwwroot/seo-traffic-bot

# 克隆代码
git clone https://github.com/PhoebeLi210/seo-traffic-bot.git .
```

或在宝塔面板中：
- 进入「文件」→ 找到 `/www/wwwroot` 目录
- 点击「上传」→ 上传zip文件或远程下载

#### 2. 安装Python环境

在宝塔面板中：
1. 进入「软件商店」
2. 搜索并安装「Python项目管理器」
3. 打开Python项目管理器
4. 安装Python 3.10版本（如果没有）

#### 3. 创建Python项目

在Python项目管理器中：

1. 点击「添加项目」
2. 填写信息：
   - **项目名称**: `seo-traffic-bot`
   - **项目路径**: `/www/wwwroot/seo-traffic-bot`
   - **Python版本**: 3.10
   - **框架**: 自定义
   - **启动方式**: `python main.py --continuous`
   - **端口**: 不填（或填0）

3. 点击「确定」

#### 4. 安装依赖

在Python项目管理器中：
1. 找到你的项目
2. 点击「模块」
3. 点击「 requirements.txt安装 」
4. 等待安装完成

或手动安装：
```bash
cd /www/wwwroot/seo-traffic-bot
pip install -r requirements.txt
playwright install chromium
```

#### 5. 配置网站列表

编辑 `/www/wwwroot/seo-traffic-bot/config/websites.json`：

```json
{
  "websites": [
    {
      "url": "https://www.yourwebsite1.com",
      "name": "网站1",
      "enabled": true,
      "max_daily_visits": 15
    },
    {
      "url": "https://www.yourwebsite2.com",
      "name": "网站2",
      "enabled": true,
      "max_daily_visits": 15
    }
  ]
}
```

#### 6. 启动项目

在Python项目管理器中：
1. 找到你的项目
2. 点击「启动」

### 方式二：命令行部署

```bash
# 1. 登录服务器
ssh root@你的服务器IP

# 2. 安装依赖
apt-get update
apt-get install -y python3-pip python3-venv

# 3. 创建目录
mkdir -p /www/wwwroot/seo-traffic-bot
cd /www/wwwroot/seo-traffic-bot

# 4. 下载代码
git clone https://github.com/PhoebeLi210/seo-traffic-bot.git .

# 5. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 6. 安装依赖
pip install -r requirements.txt
playwright install chromium

# 7. 配置网站
vim config/websites.json

# 8. 启动（后台运行）
nohup python main.py --continuous > logs/traffic_bot.log 2>&1 &

# 9. 查看日志
tail -f logs/traffic_bot.log
```

## 📊 查看统计仪表盘

### 启动仪表盘服务

```bash
cd /www/wwwroot/seo-traffic-bot
python dashboard_server.py --port 8080
```

或在宝塔Python项目管理器中添加第二个项目：
- **项目名称**: `seo-dashboard`
- **项目路径**: `/www/wwwroot/seo-traffic-bot`
- **启动方式**: `python dashboard_server.py --port 8080`
- **端口**: 8080

### 访问仪表盘

1. **不用域名访问**（推荐测试用）：
   ```
   http://服务器IP:8080
   ```
   例如：`http://47.123.45.67:8080`

2. **使用宝塔反向代理**（可选）：
   - 宝塔面板 → 网站 → 添加站点
   - 绑定域名（如果有）
   - 设置反向代理到 `http://127.0.0.1:8080`

### 开放防火墙端口

在宝塔面板中：
1. 进入「安全」
2. 添加放行端口：
   - **端口**: 8080
   - **备注**: 统计仪表盘
3. 阿里云控制台也要放行该端口

## 🔧 配置代理池（可选但推荐）

### 使用Docker部署（最简单）

```bash
# 安装Docker（如果还没有）
curl -fsSL https://get.docker.com | bash

# 启动代理池
cd /www/wwwroot/seo-traffic-bot
docker-compose up -d proxypool redis

# 查看代理池状态
curl http://localhost:5010/get
```

### 手动部署ProxyPool

```bash
# 安装Redis
apt-get install redis-server
systemctl start redis

# 安装ProxyPool
cd /opt
git clone https://github.com/Python3WebSpider/ProxyPool.git
cd ProxyPool
pip install -r requirements.txt

# 修改配置
vim proxypool/setting.py
# 修改: REDIS_HOST = 'localhost'

# 启动
python run.py
```

## 📈 查看每日点击统计

### 方式1：Web仪表盘（推荐）

访问 `http://服务器IP:8080` 查看：
- ✅ 总访问次数
- ✅ 成功/失败次数
- ✅ 成功率
- ✅ 每个网站的点击详情
- ✅ 30天访问趋势图

### 方式2：命令行查看

```bash
cd /www/wwwroot/seo-traffic-bot
python main.py --stats
```

### 方式3：查看日志文件

```bash
# 实时查看日志
tail -f /www/wwwroot/seo-traffic-bot/logs/traffic_bot.log

# 查看统计文件
cat /www/wwwroot/seo-traffic-bot/stats/2024-01-15.json
```

## 🔄 设置开机自启

### 使用宝塔计划任务

1. 宝塔面板 → 计划任务
2. 添加任务：
   - **任务类型**: Shell脚本
   - **任务名称**: 启动SEO Traffic Bot
   - **执行周期**: 开机执行
   - **脚本内容**:
     ```bash
     cd /www/wwwroot/seo-traffic-bot
     source venv/bin/activate
     nohup python main.py --continuous > logs/traffic_bot.log 2>&1 &
     nohup python dashboard_server.py --port 8080 > logs/dashboard.log 2>&1 &
     ```

### 使用systemd服务

创建服务文件 `/etc/systemd/system/seo-traffic-bot.service`：

```ini
[Unit]
Description=SEO Traffic Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/seo-traffic-bot
Environment=PATH=/www/wwwroot/seo-traffic-bot/venv/bin
ExecStart=/www/wwwroot/seo-traffic-bot/venv/bin/python main.py --continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
systemctl daemon-reload
systemctl enable seo-traffic-bot
systemctl start seo-traffic-bot
systemctl status seo-traffic-bot
```

## 🛠️ 常见问题

### Q1: 提示"playwright未安装"

```bash
cd /www/wwwroot/seo-traffic-bot
playwright install chromium
```

### Q2: 仪表盘无法访问

1. 检查防火墙：宝塔面板 → 安全 → 放行8080端口
2. 检查阿里云安全组：控制台 → 安全组 → 入方向规则 → 添加8080端口
3. 检查服务状态：
   ```bash
   netstat -tlnp | grep 8080
   ```

### Q3: 如何修改访问频率？

编辑 `config/settings.yaml`：
```yaml
behavior:
  min_visit_interval: 120    # 最短间隔（秒）
  max_visit_interval: 300    # 最长间隔（秒）
  min_stay_duration: 10      # 最短停留（秒）
  max_stay_duration: 30      # 最长停留（秒）
```

### Q4: 如何停止服务？

```bash
# 查找进程
ps aux | grep "python main.py"

# 停止进程
kill -9 进程ID

# 或使用pkill
pkill -f "python main.py"
```

## 📞 技术支持

如有问题，请查看：
- GitHub Issues: https://github.com/PhoebeLi210/seo-traffic-bot/issues
- 日志文件: `/www/wwwroot/seo-traffic-bot/logs/traffic_bot.log`

## ✅ 部署检查清单

- [ ] 代码上传到 `/www/wwwroot/seo-traffic-bot`
- [ ] Python 3.8+ 已安装
- [ ] 依赖包安装完成
- [ ] Playwright浏览器已安装
- [ ] 网站列表已配置
- [ ] 主程序已启动
- [ ] 仪表盘服务已启动
- [ ] 防火墙8080端口已开放
- [ ] 阿里云安全组8080端口已开放
- [ ] 可以通过 `http://IP:8080` 访问仪表盘

---

**祝你部署顺利！** 🎉
