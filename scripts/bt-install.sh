#!/bin/bash

# SEO Traffic Bot - 宝塔面板一键安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_NAME="seo-traffic-bot"
PROJECT_DIR="/www/wwwroot/${PROJECT_NAME}"
PYTHON_VERSION="3.10"
DASHBOARD_PORT=8080

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           SEO Traffic Bot - 宝塔一键安装脚本             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查宝塔面板
if [ ! -f "/www/server/panel/class/panelTask.py" ]; then
    echo -e "${YELLOW}⚠️ 未检测到宝塔面板，是否继续？[y/N]${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}📋 安装信息:${NC}"
echo "  项目名称: ${PROJECT_NAME}"
echo "  安装目录: ${PROJECT_DIR}"
echo "  Python版本: ${PYTHON_VERSION}"
echo "  仪表盘端口: ${DASHBOARD_PORT}"
echo ""

echo -e "${YELLOW}⚠️ 按回车键开始安装，或按 Ctrl+C 取消...${NC}"
read

# 步骤1: 创建目录
echo -e "${BLUE}[1/8] 创建项目目录...${NC}"
mkdir -p ${PROJECT_DIR}
cd ${PROJECT_DIR}

# 步骤2: 下载代码
echo -e "${BLUE}[2/8] 下载项目代码...${NC}"
if [ -d ".git" ]; then
    echo -e "${YELLOW}⚠️ 目录已存在git仓库，执行git pull...${NC}"
    git pull
else
    git clone https://github.com/PhoebeLi210/seo-traffic-bot.git .
fi

# 步骤3: 检查Python版本
echo -e "${BLUE}[3/8] 检查Python环境...${NC}"
if command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${YELLOW}⚠️ 未检测到Python3，尝试安装...${NC}"
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}✅ 使用Python: $(${PYTHON_CMD} --version)${NC}"

# 步骤4: 创建虚拟环境
echo -e "${BLUE}[4/8] 创建Python虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    ${PYTHON_CMD} -m venv venv
fi
source venv/bin/activate

# 步骤5: 安装依赖
echo -e "${BLUE}[5/8] 安装Python依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 步骤6: 安装Playwright浏览器
echo -e "${BLUE}[6/8] 安装Playwright浏览器...${NC}"
playwright install chromium

# 步骤7: 创建必要目录
echo -e "${BLUE}[7/8] 创建日志和统计目录...${NC}"
mkdir -p logs stats

# 步骤8: 配置网站列表
echo -e "${BLUE}[8/8] 配置检查...${NC}"
if [ ! -f "config/websites.json" ]; then
    echo -e "${YELLOW}⚠️ 网站配置文件不存在，从示例复制...${NC}"
    cp config/websites.json config/websites.json.bak 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ 安装完成！${NC}"
echo ""

# 显示配置信息
echo -e "${BLUE}📊 配置信息:${NC}"
echo "  项目路径: ${PROJECT_DIR}"
echo "  配置文件: ${PROJECT_DIR}/config/websites.json"
echo "  日志文件: ${PROJECT_DIR}/logs/traffic_bot.log"
echo "  统计数据: ${PROJECT_DIR}/stats/"
echo ""

# 显示下一步操作
echo -e "${BLUE}🚀 下一步操作:${NC}"
echo ""
echo "1. 编辑网站配置:"
echo -e "   ${YELLOW}vim ${PROJECT_DIR}/config/websites.json${NC}"
echo ""
echo "2. 启动流量机器人:"
echo -e "   ${YELLOW}cd ${PROJECT_DIR} && python main.py --continuous${NC}"
echo ""
echo "3. 启动统计仪表盘:"
echo -e "   ${YELLOW}cd ${PROJECT_DIR} && python dashboard_server.py --port ${DASHBOARD_PORT}${NC}"
echo ""
echo "4. 访问统计仪表盘:"
echo -e "   ${GREEN}http://你的服务器IP:${DASHBOARD_PORT}${NC}"
echo ""

# 防火墙提示
echo -e "${YELLOW}⚠️ 重要提示:${NC}"
echo "  请在宝塔面板和阿里云安全组中放行端口:"
echo "  - ${DASHBOARD_PORT} (统计仪表盘)"
echo "  - 5010 (代理池，可选)"
echo ""

# 询问是否创建宝塔Python项目
if [ -f "/www/server/panel/class/panelTask.py" ]; then
    echo -e "${BLUE}💡 是否自动创建宝塔Python项目? [y/N]${NC}"
    read -r create_project
    
    if [[ "$create_project" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${BLUE}正在创建宝塔Python项目...${NC}"
        
        # 创建项目配置文件
        cat > bt_project.json << EOF
{
  "project_name": "${PROJECT_NAME}",
  "project_path": "${PROJECT_DIR}",
  "project_cmd": "cd ${PROJECT_DIR} && source venv/bin/activate && python main.py --continuous",
  "project_log": "${PROJECT_DIR}/logs/traffic_bot.log"
}
EOF
        
        echo -e "${GREEN}✅ 项目配置已保存到: ${PROJECT_DIR}/bt_project.json${NC}"
        echo -e "${YELLOW}请手动在宝塔Python项目管理器中导入此配置${NC}"
    fi
fi

# 询问是否立即启动
echo ""
echo -e "${BLUE}🚀 是否立即启动服务? [y/N]${NC}"
read -r start_now

if [[ "$start_now" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}启动流量机器人...${NC}"
    nohup python main.py --continuous > logs/traffic_bot.log 2>&1 &
    echo -e "${GREEN}✅ 流量机器人已启动 (PID: $!)${NC}"
    
    echo -e "${BLUE}启动统计仪表盘...${NC}"
    nohup python dashboard_server.py --port ${DASHBOARD_PORT} > logs/dashboard.log 2>&1 &
    echo -e "${GREEN}✅ 统计仪表盘已启动 (PID: $!)${NC}"
    
    echo ""
    echo -e "${GREEN}🎉 所有服务已启动！${NC}"
    echo -e "访问统计仪表盘: ${GREEN}http://$(curl -s ip.sb):${DASHBOARD_PORT}${NC}"
fi

echo ""
echo -e "${GREEN}安装脚本执行完毕！${NC}"
echo ""
