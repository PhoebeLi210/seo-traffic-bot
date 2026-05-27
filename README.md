# SEO Traffic Bot

🚀 **自动化网站流量生成工具** - 为你的网站生成自然、真实的访问流量，提升SEO排名。

## ✨ 功能特性

- 🤖 **智能反检测**: 使用Playwright + 反检测脚本，模拟真实浏览器指纹
- 🎭 **真实行为模拟**: 随机滚动、鼠标移动、点击链接，模拟真实用户
- 🌐 **代理池集成**: 支持ProxyPool代理池，自动轮换IP地址
- 📊 **访问统计**: 详细的访问日志和统计报告
- ⚙️ **灵活配置**: JSON/YAML配置文件，环境变量支持
- 🐳 **Docker部署**: 一键Docker Compose部署
- 📝 **中文界面**: 全中文日志输出和配置说明

## 🛠️ 技术栈

- **核心框架**: [Playwright](https://playwright.dev/python/) - 现代自动化浏览器工具
- **反检测**: 自定义反检测脚本 + 随机UA/视口/时区
- **代理池**: [ProxyPool](https://github.com/Python3WebSpider/ProxyPool) - 开源代理池
- **配置管理**: Pydantic + PyYAML
- **日志系统**: Loguru

## 📦 安装

### 方式一：本地安装

```bash
# 克隆仓库
git clone https://github.com/PhoebeLi210/seo-traffic-bot.git
cd seo-traffic-bot

# 运行安装脚本
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 方式二：Docker部署（推荐）

```bash
# 启动所有服务（包含代理池）
docker-compose up -d

# 查看日志
docker-compose logs -f traffic-bot
```

## ⚙️ 配置

### 1. 配置目标网站

编辑 `config/websites.json`:

```json
{
  "websites": [
    {
      "url": "https://www.yourwebsite1.com",
      "name": "我的网站1",
      "enabled": true,
      "keywords": ["关键词1", "关键词2"],
      "max_daily_visits": 15
    },
    {
      "url": "https://www.yourwebsite2.com",
      "name": "我的网站2",
      "enabled": true,
      "max_daily_visits": 10
    }
  ]
}
```

### 2. 配置行为参数

编辑 `config/settings.yaml`:

```yaml
# 行为模拟设置
behavior:
  min_stay_duration: 10      # 最短停留时间（秒）
  max_stay_duration: 30      # 最长停留时间（秒）
  min_visit_interval: 120    # 最短访问间隔（秒）
  max_visit_interval: 300    # 最长访问间隔（秒）
  
  scroll:
    enabled: true
    min_scrolls: 2
    max_scrolls: 5
  
  click:
    enabled: true
    click_probability: 0.4   # 40%概率点击链接

# 代理设置
proxy:
  enabled: true
  api_url: "http://127.0.0.1:5010/get"
```

### 3. 环境变量（可选）

复制 `.env.example` 为 `.env` 并编辑：

```bash
cp .env.example .env
```

## 🚀 使用

### 运行一次

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行一次所有网站
python main.py
```

### 持续运行模式

```bash
# 持续循环访问
python main.py --continuous

# 或使用脚本
./scripts/start.sh continuous
```

### 查看统计

```bash
python main.py --stats
```

### 查看配置

```bash
python main.py --config
```

## 📊 项目结构

```
seo-traffic-bot/
├── config/
│   ├── websites.json       # 网站配置
│   └── settings.yaml       # 行为参数配置
├── src/
│   ├── __init__.py
│   ├── config_manager.py   # 配置管理
│   ├── proxy_manager.py    # 代理管理
│   ├── stealth_enhancer.py # 反检测增强
│   ├── behavior_simulator.py # 行为模拟
│   ├── visitor.py          # 网站访问
│   └── monitor.py          # 监控统计
├── scripts/
│   ├── setup.sh            # 安装脚本
│   └── start.sh            # 启动脚本
├── logs/                   # 日志文件
├── stats/                  # 统计数据
├── main.py                 # 主程序
├── requirements.txt        # Python依赖
├── Dockerfile             # Docker镜像
├── docker-compose.yml     # Docker编排
└── README.md              # 本文件
```

## 🔧 代理池部署

### 使用Docker（推荐）

```bash
# 启动代理池和Redis
docker-compose up -d proxypool redis

# 查看代理池状态
curl http://localhost:5010/get
```

### 手动部署

```bash
# 安装Redis
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# 安装ProxyPool
git clone https://github.com/Python3WebSpider/ProxyPool.git
cd ProxyPool
pip install -r requirements.txt

# 启动服务
python run.py
```

## ⚠️ 注意事项

1. **访问频率**: 建议每个网站每天5-20次访问，过于频繁可能适得其反
2. **代理质量**: 使用高质量的代理IP效果更好
3. **行为随机**: 工具已内置随机化，避免形成固定模式
4. **法律合规**: 请确保你的使用符合当地法律法规和网站服务条款

## 📝 日志说明

日志文件保存在 `logs/traffic_bot.log`，包含：
- 每次访问的详细记录
- 成功/失败状态
- 停留时间和访问页面数
- 错误信息

## 📈 统计数据

统计数据保存在 `stats/` 目录，按日期存储：
- 总访问次数
- 成功率
- 各网站访问情况
- 平均停留时间

## 🔒 隐私与安全

- 所有配置和数据都保存在本地
- 不收集任何用户数据
- 代理池可自建，不依赖第三方服务

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 💡 提示

- 首次运行前请确保已配置目标网站
- 建议在测试环境先验证配置
- 可以先用 `--stats` 查看当前状态
- 遇到问题请查看日志文件

---

**祝你网站排名节节高升！** 🎉
