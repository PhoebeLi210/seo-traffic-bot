# Google Search Console API 服务账号配置指南

## 概述
通过服务账号（Service Account）认证，无需浏览器交互即可访问 Google Search Console 数据。

---

## 步骤 1：创建 Google Cloud 项目

1. 在能访问 Google 的电脑上（开 VPN），登录 https://console.cloud.google.com/
2. 点击顶部导航栏的项目选择器，点击 **"新建项目"**
3. 项目名称填写：`seo-traffic-bot`（或其他名称）
4. 点击 **"创建"**，等待项目创建完成（约 30 秒）
5. 点击顶部导航栏，选择刚创建的项目

---

## 步骤 2：启用 Google Search Console API

1. 在左侧菜单点击 **"API 和服务" > "库"**
2. 搜索框输入：`Google Search Console API`
3. 点击搜索结果进入 API 详情页
4. 点击 **"启用"** 按钮

---

## 步骤 3：创建服务账号

1. 左侧菜单点击 **"API 和服务" > "凭据"**
2. 点击顶部 **"创建凭据" > "服务账号"**
3. 填写信息：
   - **服务账号名称**：`gsc-reader`
   - **服务账号 ID**：自动生成（如 `gsc-reader@seo-traffic-bot.iam.gserviceaccount.com`）
   - **描述**：`用于读取 Search Console 数据`
4. 点击 **"创建并继续"**
5. **角色选择**：
   - 点击 "选择角色"
   - 搜索 `Service Account User`
   - 选择 **"服务账号用户"**
6. 点击 **"继续"**，再点击 **"完成"**

---

## 步骤 4：创建并下载密钥文件

1. 在 "凭据" 页面，找到刚创建的服务账号
2. 点击服务账号名称进入详情页
3. 点击顶部 **"密钥"** 标签
4. 点击 **"添加密钥" > "创建新密钥"**
5. 密钥类型选择 **"JSON"**
6. 点击 **"创建"**
7. JSON 文件会自动下载到本地（文件名类似 `seo-traffic-bot-xxxxx.json`）
8. **重要**：保存好这个文件，不要泄露！

---

## 步骤 5：在 Google Search Console 中授权服务账号

1. 登录 https://search.google.com/search-console
2. 选择你要查询的网站属性
3. 左侧菜单点击 **"设置"**（齿轮图标）
4. 点击 **"用户和权限"**
5. 点击 **"添加用户"**
6. 输入服务账号邮箱地址（格式：`gsc-reader@seo-traffic-bot.iam.gserviceaccount.com`）
   - 邮箱地址可以在下载的 JSON 文件中找到 `client_email` 字段
7. 权限选择 **"受限"**（只能读取数据，不能修改）
8. 点击 **"添加"**

**注意**：需要为每个要查询的网站都添加这个服务账号。

---

## 步骤 6：上传密钥文件到服务器

### 方式 A：通过宝塔面板上传

1. 登录宝塔面板
2. 进入 **"文件"** 功能
3. 导航到 `/www/wwwroot/zhongshunbaode.com/stats/config/`
4. 如果 `config` 目录不存在，先创建
5. 上传下载的 JSON 文件
6. 重命名为 `gsc_credentials.json`

### 方式 B：通过 SSH 上传

在本地电脑执行（需要先安装 scp 或使用 SFTP 工具如 FileZilla）：

```bash
scp ~/Downloads/seo-traffic-bot-xxxxx.json root@你的服务器IP:/www/wwwroot/zhongshunbaode.com/stats/config/gsc_credentials.json
```

---

## 步骤 7：安装 Google API Python 库

在服务器 SSH 上执行：

```bash
/www/server/python_manager/versions/3.10.0/bin/python3.10 -m pip install google-auth google-auth-oauthlib google-api-python-client --break-system-packages
```

---

## 步骤 8：验证配置

在服务器 SSH 上执行：

```bash
cd /www/wwwroot/zhongshunbaode.com/stats
/www/server/python_manager/versions/3.10.0/bin/python3.10 -c "
from src.gsc_keyword_recommender import gsc_recommender
status = gsc_recommender.check_credentials_setup()
print('凭证状态:', status)
"
```

如果显示 `configured: True`，说明配置成功！

---

## JSON 文件格式示例

上传后的 `gsc_credentials.json` 内容格式：

```json
{
  "type": "service_account",
  "project_id": "seo-traffic-bot",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "gsc-reader@seo-traffic-bot.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

---

## 常见问题

### Q: 服务账号邮箱在哪里找？
A: 在下载的 JSON 文件中，找到 `client_email` 字段。

### Q: 权限选"完整"还是"受限"？
A: 选"受限"即可，只需要读取数据，不需要修改权限。

### Q: 多个网站怎么办？
A: 在 Search Console 中为每个网站属性都添加同一个服务账号。

### Q: 密钥文件泄露了怎么办？
A: 在 Google Cloud Console 的服务账号详情页，删除泄露的密钥，重新创建新密钥。

---

## 完成后效果

配置完成后，在 SEO Traffic Bot 仪表盘中：
1. 添加/编辑网站时点击 **"获取GSC推荐关键词"**
2. 系统会从 Google Search Console 获取真实的排名 4-20 位关键词
3. 显示提示：`✓ 成功添加 X 个推荐关键词（来自GSC真实数据）`