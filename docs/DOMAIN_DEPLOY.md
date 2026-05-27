# 域名部署指南 - zhongshunbaode.com

本文档介绍如何使用域名 `zhongshunbaode.com` 部署SEO Traffic Bot多用户版本。

## 📋 域名规划

| 域名 | 用途 | 说明 |
|------|------|------|
| `zhongshunbaode.com` | 项目落地页 | 介绍产品、价格、注册入口 |
| `stats.zhongshunbaode.com` | 用户仪表盘 | 登录后查看统计、管理网站 |
| `api.zhongshunbaode.com` | API接口 | 程序调用接口（可选） |

## 🚀 部署步骤

### 第一步：DNS解析配置

登录你的域名服务商控制台，添加以下解析记录：

```
类型    主机记录           记录值（你的服务器IP）
A       @                 47.xxx.xxx.xxx
A       stats             47.xxx.xxx.xxx
A       api               47.xxx.xxx.xxx
```

### 第二步：宝塔面板配置

#### 1. 创建主网站（落地页）

1. 宝塔面板 → 网站 → 添加站点
2. 填写信息：
   - **域名**: `zhongshunbaode.com`
   - **根目录**: `/www/wwwroot/zhongshunbaode.com`
   - **PHP版本**: 纯静态
3. 点击「提交」

4. 上传落地页文件：
   ```bash
   # 在服务器上执行
   mkdir -p /www/wwwroot/zhongshunbaode.com
   cd /www/wwwroot/zhongshunbaode.com
   
   # 从GitHub下载
   git clone https://github.com/PhoebeLi210/seo-traffic-bot.git /tmp/seo-bot
   cp -r /tmp/seo-bot/landing_page/* .
   rm -rf /tmp/seo-bot
   ```

#### 2. 申请SSL证书

1. 宝塔面板 → 网站 → 找到 `zhongshunbaode.com`
2. 点击「设置」→ SSL → Let's Encrypt
3. 勾选「强制HTTPS」
4. 同样为 `stats.zhongshunbaode.com` 申请证书

#### 3. 创建子域名网站（仪表盘）

1. 宝塔面板 → 网站 → 添加站点
2. 填写信息：
   - **域名**: `stats.zhongshunbaode.com`
   - **根目录**: `/www/wwwroot/seo-traffic-bot`
   - **PHP版本**: 纯静态
3. 点击「提交」

#### 4. 配置Nginx反向代理

为 `stats.zhongshunbaode.com` 配置反向代理：

1. 宝塔面板 → 网站 → 找到 `stats.zhongshunbaode.com`
2. 点击「设置」→ 反向代理
3. 添加反向代理：
   - **代理名称**: dashboard
   - **目标URL**: `http://127.0.0.1:8081`
   - **发送域名**: `$host`

4. 在「配置文件」中添加WebSocket支持：
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:8081;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection 'upgrade';
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_cache_bypass $http_upgrade;
   }
   ```

### 第三步：部署SEO Traffic Bot

#### 1. 下载代码

```bash
cd /www/wwwroot
git clone https://github.com/PhoebeLi210/seo-traffic-bot.git
```

#### 2. 安装依赖

```bash
cd /www/wwwroot/seo-traffic-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

#### 3. 创建数据目录

```bash
mkdir -p data/users data/user_data logs stats
```

#### 4. 修改配置

编辑 `config/settings.yaml`，修改端口：
```yaml
# 避免与另一个脚本的8080端口冲突
monitoring:
  dashboard_port: 8081
```

### 第四步：启动服务

#### 方法1：使用宝塔Python项目管理器

1. 宝塔面板 → 软件商店 → Python项目管理器
2. 添加项目：
   - **项目名称**: `seo-traffic-bot`
   - **项目路径**: `/www/wwwroot/seo-traffic-bot`
   - **Python版本**: 3.10
   - **启动命令**: `source venv/bin/activate && python multi_user_server.py`
   - **端口**: 8081

#### 方法2：命令行启动

```bash
cd /www/wwwroot/seo-traffic-bot
source venv/bin/activate

# 启动多用户服务
nohup python multi_user_server.py > logs/server.log 2>&1 &
```

### 第五步：设置开机自启

宝塔面板 → 计划任务 → 添加任务：
- **任务类型**: Shell脚本
- **任务名称**: 启动SEO Traffic Bot
- **执行周期**: 开机执行
- **脚本内容**:
  ```bash
  cd /www/wwwroot/seo-traffic-bot
  source venv/bin/activate
  nohup python multi_user_server.py > logs/server.log 2>&1 &
  ```

## 🔧 防火墙配置

确保以下端口已开放：

| 端口 | 用途 | 是否对外 |
|------|------|----------|
| 80 | HTTP | 是 |
| 443 | HTTPS | 是 |
| 8081 | 仪表盘服务 | 否（仅本地） |

宝塔面板 → 安全 → 放行端口：
- 放行 80、443 端口
- **不需要**放行 8081（通过Nginx反向代理访问）

阿里云控制台 → 安全组 → 入方向规则：
- 放行 80、443 端口

## 📊 访问地址

部署完成后，可以通过以下地址访问：

| 地址 | 说明 |
|------|------|
| `https://zhongshunbaode.com` | 项目落地页 |
| `https://stats.zhongshunbaode.com` | 用户仪表盘（登录/注册） |

## 📝 用户注册流程

1. 访问 `https://stats.zhongshunbaode.com/register`
2. 填写用户名、邮箱、密码
3. 系统自动创建用户数据目录
4. 登录后可以：
   - 添加管理网站
   - 查看访问统计
   - 获取API密钥

## 🛠️ 常见问题

### Q1: 提示"端口被占用"

修改 `multi_user_server.py` 中的端口：
```python
PORT = 8082  # 改为其他端口
```

同时更新Nginx反向代理配置。

### Q2: 无法访问子域名

1. 检查DNS解析是否生效：
   ```bash
   nslookup stats.zhongshunbaode.com
   ```

2. 检查宝塔网站配置是否正确

3. 检查Nginx配置：
   ```bash
   nginx -t
   systemctl restart nginx
   ```

### Q3: SSL证书申请失败

1. 确保域名已正确解析到服务器
2. 等待DNS生效（通常10-30分钟）
3. 检查80端口是否被占用
4. 尝试手动申请：
   ```bash
   certbot certonly --standalone -d stats.zhongshunbaode.com
   ```

### Q4: 如何添加更多用户

用户可以通过注册页面自助注册，或者你作为管理员手动添加：

```python
from src.user_manager import user_manager

# 创建用户
user = user_manager.register("friend1", "friend1@email.com", "password123")
print(f"API Key: {user.api_key}")
```

## 🔒 安全建议

1. **定期备份数据**：
   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz data/ stats/ logs/
   ```

2. **修改默认配置**：
   - 修改 `src/user_manager.py` 中的默认套餐限制
   - 设置强密码策略

3. **监控日志**：
   ```bash
   tail -f /www/wwwroot/seo-traffic-bot/logs/server.log
   ```

## 📞 技术支持

如有问题，请查看：
- GitHub Issues: https://github.com/PhoebeLi210/seo-traffic-bot/issues
- 日志文件: `/www/wwwroot/seo-traffic-bot/logs/server.log`

---

**部署完成！** 🎉

现在你可以：
1. 访问 `https://zhongshunbaode.com` 查看落地页
2. 访问 `https://stats.zhongshunbaode.com` 注册账号
3. 邀请朋友注册使用
