#!/bin/bash

# SEO Traffic Bot - Alibaba Cloud Linux 3 一键部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SEO Traffic Bot - Alibaba Cloud Linux 3 一键部署        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 请使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查系统
if [ ! -f "/etc/alinux-release" ]; then
    echo -e "${YELLOW}⚠️ 未检测到 Alibaba Cloud Linux，是否继续？[y/N]${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}📋 开始部署...${NC}"

# 步骤1: 安装Docker
echo -e "${BLUE}[1/6] 检查并安装Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️ Docker未安装，正在安装...${NC}"
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}✅ Docker安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker已安装${NC}"
fi

# 步骤2: 安装Docker Compose
echo -e "${BLUE}[2/6] 检查并安装Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️ Docker Compose未安装，正在安装...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose安装完成${NC}"
else
    echo -e "${GREEN}✅ Docker Compose已安装${NC}"
fi

# 步骤3: 进入项目目录
echo -e "${BLUE}[3/6] 检查项目目录...${NC}"
PROJECT_DIR="/www/wwwroot/zhongshunbaode.com/stats"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 项目目录不存在: $PROJECT_DIR${NC}"
    echo -e "${YELLOW}请先创建目录并克隆代码${NC}"
    exit 1
fi

cd "$PROJECT_DIR"
echo -e "${GREEN}✅ 进入项目目录: $PROJECT_DIR${NC}"

# 步骤4: 构建Docker镜像
echo -e "${BLUE}[4/6] 构建Docker镜像...${NC}"
docker-compose -f docker-compose.alibaba.yml build
echo -e "${GREEN}✅ Docker镜像构建完成${NC}"

# 步骤5: 启动服务
echo -e "${BLUE}[5/6] 启动服务...${NC}"
docker-compose -f docker-compose.alibaba.yml up -d
echo -e "${GREEN}✅ 服务已启动${NC}"

# 步骤6: 检查状态
echo -e "${BLUE}[6/6] 检查服务状态...${NC}"
sleep 3

if docker ps | grep -q "seo-traffic-bot"; then
    echo -e "${GREEN}✅ 服务运行正常${NC}"
else
    echo -e "${RED}❌ 服务启动失败，请检查日志${NC}"
    docker-compose -f docker-compose.alibaba.yml logs
    exit 1
fi

# 显示信息
echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo -e "${BLUE}📊 服务信息:${NC}"
echo "  容器名称: seo-traffic-bot"
echo "  访问端口: 8081"
echo "  数据目录: $PROJECT_DIR/data"
echo "  日志目录: $PROJECT_DIR/logs"
echo ""
echo -e "${BLUE}🛠️ 常用命令:${NC}"
echo "  查看日志: docker logs -f seo-traffic-bot"
echo "  停止服务: docker-compose -f docker-compose.alibaba.yml down"
echo "  重启服务: docker-compose -f docker-compose.alibaba.yml restart"
echo "  进入容器: docker exec -it seo-traffic-bot bash"
echo ""
echo -e "${BLUE}🌐 访问地址:${NC}"
echo "  仪表盘: http://stats.zhongshunbaode.com"
echo ""
echo -e "${YELLOW}⚠️ 请确保已在宝塔面板配置Nginx反向代理到 8081 端口${NC}"
echo ""
