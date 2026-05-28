"""
Dashboard服务器 - HTTP服务器主入口
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from .models.session import SessionManager, session_manager
from .services.user_service import UserService, user_service
from .services.website_service import WebsiteService, website_service
from .services.task_service import TaskService, task_service
from .services.rank_service import RankService, rank_service
from .services.stats_service import StatsService, stats_service
from .services.keyword_service import KeywordService, keyword_service
from .routes.auth import AuthHandler
from .routes.website import WebsiteHandler
from .routes.task import TaskHandler
from .routes.rank import RankHandler
from .routes.stats import StatsHandler


class DashboardServer:
    """模块化Dashboard服务器"""

    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.server_thread = None

        # 初始化服务
        self.session_manager = session_manager
        self.user_service = user_service
        self.website_service = website_service
        self.task_service = task_service
        self.rank_service = rank_service
        self.stats_service = stats_service
        self.keyword_service = keyword_service

        # 初始化路由处理器
        self.auth_handler = AuthHandler(
            session_manager=self.session_manager,
            user_service=self.user_service,
            template_renderer=self.render_template
        )
        self.website_handler = WebsiteHandler(
            session_manager=self.session_manager,
            website_service=self.website_service,
            user_service=self.user_service
        )
        self.task_handler = TaskHandler(
            session_manager=self.session_manager,
            task_service=self.task_service
        )
        self.rank_handler = RankHandler(
            session_manager=self.session_manager,
            rank_service=self.rank_service,
            keyword_service=self.keyword_service
        )
        self.stats_handler = StatsHandler(
            session_manager=self.session_manager,
            stats_service=self.stats_service
        )

        # 模板目录
        self.template_dir = Path(__file__).parent / "templates"

    def render_template(self, template_name: str, **kwargs) -> str:
        """
        渲染HTML模板

        Args:
            template_name: 模板文件名
            **kwargs: 模板变量

        Returns:
            渲染后的HTML字符串
        """
        template_path = self.template_dir / template_name
        if not template_path.exists():
            return f"<h1>Template not found: {template_name}</h1>"

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 简单的模板替换
        for key, value in kwargs.items():
            if value is None:
                value = ''
            content = content.replace(f'{{{{{key}}}}}', str(value))

        # 处理条件块 {% if xxx %}...{% endif %}
        import re
        content = re.sub(r'\{% if (\w+) %\}', '', content)
        content = re.sub(r'\{% endif %\}', '', content)

        return content

    def generate_dashboard_page(self, user_id: str) -> str:
        """生成仪表盘页面"""
        user = self.user_service.get_user(user_id)
        if not user:
            return self.render_template('login.html', error='请先登录')

        websites = self.website_service.load_websites(user_id)
        stats = self.stats_service.get_stats(user_id, days=7)

        # 生成网站列表行
        website_rows = ""
        for i, ws in enumerate(websites):
            url = ws.get("url", "")
            keywords = ws.get("keywords", [])
            daily_visits = ws.get("daily_visits", 10)
            enabled = ws.get("enabled", True)
            status_badge = '<span class="badge badge-success">运行中</span>' if enabled else '<span class="badge badge-gray">已暂停</span>'
            kw_text = ", ".join(keywords[:3]) + (f" (+{len(keywords)-3})" if len(keywords) > 3 else "") if keywords else '<span class="text-muted">未设置</span>'
            website_rows += f"""
            <tr data-index="{i}">
                <td><a href="{url}" target="_blank" class="url-link">{url[:45]}{'...' if len(url)>45 else ''}</a></td>
                <td>{kw_text}</td>
                <td class="center">{daily_visits}</td>
                <td class="center">{status_badge}</td>
                <td class="center">
                    <button class="btn btn-sm btn-primary" onclick="editSite({i})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSite({i})">删除</button>
                </td>
            </tr>"""

        if not website_rows:
            website_rows = """<tr><td colspan="5" class="empty-state">
                <div class="empty-icon">🌐</div>
                <p>还没有添加网站</p>
                <p class="text-muted">点击上方"添加网站"按钮开始</p>
            </td></tr>"""

        # 生成统计行
        stats_rows = ""
        for url, data in sorted(stats["website_summary"].items(), key=lambda x: x[1]["visits"], reverse=True):
            rate = (data["success"] / data["visits"] * 100) if data["visits"] > 0 else 0
            stats_rows += f"""
            <tr>
                <td class="url-cell">{url[:50]}{'...' if len(url)>50 else ''}</td>
                <td class="center">{data['visits']}</td>
                <td class="center text-success">{data['success']}</td>
                <td class="center text-danger">{data['failed']}</td>
                <td class="center">{rate:.1f}%</td>
            </tr>"""
        if not stats_rows:
            stats_rows = """<tr><td colspan="5" class="empty-state">
                <div class="empty-icon">📊</div>
                <p>暂无统计数据</p>
                <p class="text-muted">添加网站并运行后，这里会显示访问数据</p>
            </td></tr>"""

        # 准备网站数据给JS
        websites_json = json.dumps(websites, ensure_ascii=False)

        return self.render_template(
            'dashboard.html',
            username=user.username,
            plan=user.plan.upper(),
            website_count=len(websites),
            max_websites=user.max_websites,
            max_daily_visits=user.max_daily_visits,
            total_visits=stats['total_visits'],
            success_visits=stats['success_visits'],
            success_rate=f"{stats['success_rate']:.1f}",
            website_rows=website_rows,
            stats_rows=stats_rows,
            websites_json=websites_json
        )

    def _get_cookie(self, headers) -> Dict[str, str]:
        """从请求头解析cookies"""
        cookie_header = headers.get('Cookie', '')
        cookies = {}
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                key, value = cookie.strip().split('=', 1)
                cookies[key] = value
        return cookies

    def _check_login(self, cookies: Dict[str, str]) -> Optional[str]:
        """检查登录状态，返回user_id"""
        session_id = cookies.get('session_id')
        if not session_id:
            return None
        return self.session_manager.get_user_id(session_id)

    def start_server(self):
        """启动Web服务器"""
        dashboard = self

        class DashboardHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path
                cookies = dashboard._get_cookie(self.headers)
                query_params = parse_qs(parsed_path.query)

                # 首页重定向
                if path == '/' or path == '/dashboard':
                    user_id = dashboard._check_login(cookies)
                    if not user_id:
                        self._redirect('/login')
                        return
                    html = dashboard.generate_dashboard_page(user_id)
                    self._send_html(html)
                    return

                # 认证路由
                if path == '/login':
                    result = dashboard.auth_handler.handle_get_login(cookies)
                    if 'redirect' in result:
                        self._redirect(result['redirect'])
                    else:
                        self._send_html(result.get('html', ''))
                    return

                if path == '/register':
                    result = dashboard.auth_handler.handle_get_register(cookies)
                    if 'redirect' in result:
                        self._redirect(result['redirect'])
                    else:
                        self._send_html(result.get('html', ''))
                    return

                if path == '/logout':
                    result = dashboard.auth_handler.handle_get_logout(cookies)
                    self._redirect(result.get('redirect', '/login'), clear_cookie='session_id')
                    return

                # API路由
                if path == '/api/stats':
                    result = dashboard.stats_handler.handle_get_stats(cookies, query_params)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/websites':
                    result = dashboard.website_handler.handle_get_websites(cookies)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/user':
                    result = dashboard.website_handler.handle_get_user_info(cookies)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/rank':
                    result = dashboard.rank_handler.handle_get_rank(cookies, query_params)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/baidu_recommend':
                    result = dashboard.rank_handler.handle_get_baidu_recommend(cookies, query_params)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/tasks':
                    result = dashboard.task_handler.handle_get_tasks(cookies, query_params)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/task_stats':
                    result = dashboard.task_handler.handle_get_task_stats(cookies)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                if path == '/api/trend_data':
                    result = dashboard.stats_handler.handle_get_trend_data(cookies, query_params)
                    if 'error' in result and result.get('status') == 401:
                        self._send_json(result, 401)
                    else:
                        self._send_json(result)
                    return

                # 404
                self._send_html('<h1>404 - 页面不存在</h1>', 404)

            def do_POST(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path

                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')

                cookies = dashboard._get_cookie(self.headers)

                # 判断是否为JSON
                try:
                    params = json.loads(post_data)
                except (json.JSONDecodeError, ValueError):
                    params = parse_qs(post_data)

                # 认证路由
                if path == '/login':
                    result = dashboard.auth_handler.handle_post_login(params, cookies)
                    if 'redirect' in result:
                        self._redirect(result['redirect'], cookies=result.get('cookies'))
                    else:
                        self._send_html(result.get('html', ''), result.get('status', 400))
                    return

                if path == '/register':
                    result = dashboard.auth_handler.handle_post_register(params)
                    if 'redirect' in result:
                        self._redirect(result['redirect'], cookies=result.get('cookies'))
                    else:
                        self._send_html(result.get('html', ''), result.get('status', 400))
                    return

                # API路由
                if path == '/api/websites':
                    result = dashboard.website_handler.handle_post_websites(cookies, post_data)
                    status = result.pop('status', 200) if isinstance(result, dict) else 200
                    self._send_json(result, status)
                    return

                if path == '/api/task/toggle':
                    result = dashboard.task_handler.handle_post_toggle_task(cookies, post_data)
                    status = result.pop('status', 200) if isinstance(result, dict) else 200
                    self._send_json(result, status)
                    return

                if path == '/api/task/batch_action':
                    result = dashboard.task_handler.handle_post_batch_action(cookies, post_data)
                    status = result.pop('status', 200) if isinstance(result, dict) else 200
                    self._send_json(result, status)
                    return

                if path == '/api/task/add':
                    result = dashboard.task_handler.handle_post_add_task(cookies, post_data)
                    status = result.pop('status', 200) if isinstance(result, dict) else 200
                    self._send_json(result, status)
                    return

                # 404
                self._send_html('<h1>404 - 页面不存在</h1>', 404)

            def _send_html(self, html: str, status: int = 200):
                self.send_response(status)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _send_json(self, data: dict, status: int = 200):
                self.send_response(status)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

            def _redirect(self, location: str, cookies: dict = None, clear_cookie: str = None):
                self.send_response(302)
                self.send_header('Location', location)
                if cookies:
                    for name, value in cookies.items():
                        self.send_header('Set-Cookie', f'{name}={value}; Path=/; HttpOnly')
                if clear_cookie:
                    self.send_header('Set-Cookie', f'{clear_cookie}=; Path=/; HttpOnly; Max-Age=0')
                self.end_headers()

            def log_message(self, format, *args):
                logger.info(f"Dashboard: {args[0]}")

        self.server = HTTPServer(('0.0.0.0', self.port), DashboardHandler)

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        logger.info(f"Dashboard服务器已启动: http://0.0.0.0:{self.port}")

    def stop_server(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            logger.info("Dashboard服务器已停止")


# 全局服务器实例
dashboard_server = DashboardServer()


def start_dashboard(port: int = 8080):
    """启动Dashboard服务器"""
    server = DashboardServer(port)
    server.start_server()
    return server


if __name__ == '__main__':
    start_dashboard(8080)
