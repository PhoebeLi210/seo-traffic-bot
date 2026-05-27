"""
多用户Web仪表盘 - 支持用户登录和数据隔离
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote
import threading
from loguru import logger

from .user_manager import user_manager, User
from .web_dashboard import StatsDashboard


class MultiUserDashboard:
    """多用户仪表盘"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.server_thread = None
        self.sessions: Dict[str, str] = {}  # session_id -> user_id
    
    def get_user_dashboard(self, user_id: str) -> StatsDashboard:
        """获取用户的仪表盘实例"""
        user_dir = user_manager.get_user_data_dir(user_id)
        return StatsDashboard(stats_dir=str(user_dir / "stats"))
    
    def generate_login_page(self, error: str = None) -> str:
        """生成登录页面"""
        error_html = f'<div class="error">{error}</div>' if error else ''
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - SEO Traffic Bot</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-box {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 1.8em;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }}
        input {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1em;
            transition: border-color 0.3s;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .links {{
            text-align: center;
            margin-top: 20px;
        }}
        .links a {{
            color: #667eea;
            text-decoration: none;
        }}
        .links a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 用户登录</h1>
        {error_html}
        <form method="POST" action="/login">
            <div class="form-group">
                <label>用户名或邮箱</label>
                <input type="text" name="username" required placeholder="请输入用户名">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" required placeholder="请输入密码">
            </div>
            <button type="submit">登录</button>
        </form>
        <div class="links">
            <a href="/register">还没有账号？立即注册</a>
        </div>
    </div>
</body>
</html>"""
    
    def generate_register_page(self, error: str = None) -> str:
        """生成注册页面"""
        error_html = f'<div class="error">{error}</div>' if error else ''
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - SEO Traffic Bot</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .register-box {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 1.8em;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }}
        input {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1em;
            transition: border-color 0.3s;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .links {{
            text-align: center;
            margin-top: 20px;
        }}
        .links a {{
            color: #667eea;
            text-decoration: none;
        }}
        .links a:hover {{
            text-decoration: underline;
        }}
        .plan-info {{
            background: #f0f4ff;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .plan-info h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .plan-info ul {{
            list-style: none;
            color: #555;
        }}
        .plan-info li {{
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
        }}
        .plan-info li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: #10b981;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="register-box">
        <h1>📝 用户注册</h1>
        <div class="plan-info">
            <h3>免费版包含：</h3>
            <ul>
                <li>最多8个网站</li>
                <li>每日20次访问/网站</li>
                <li>基础统计数据</li>
                <li>邮件技术支持</li>
            </ul>
        </div>
        {error_html}
        <form method="POST" action="/register">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" required placeholder="设置用户名">
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" name="email" required placeholder="输入邮箱地址">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" required placeholder="设置密码（至少6位）">
            </div>
            <div class="form-group">
                <label>确认密码</label>
                <input type="password" name="password_confirm" required placeholder="再次输入密码">
            </div>
            <button type="submit">注册</button>
        </form>
        <div class="links">
            <a href="/login">已有账号？立即登录</a>
        </div>
    </div>
</body>
</html>"""
    
    def start_server(self):
        """启动Web服务器"""
        dashboard = self
        
        class MultiUserHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path
                
                # 检查登录状态
                session_id = self._get_cookie('session_id')
                user_id = dashboard.sessions.get(session_id) if session_id else None
                
                if path == '/login':
                    self._send_html(dashboard.generate_login_page())
                
                elif path == '/register':
                    self._send_html(dashboard.generate_register_page())
                
                elif path == '/logout':
                    if session_id in dashboard.sessions:
                        del dashboard.sessions[session_id]
                    self._redirect('/login')
                
                elif path == '/' or path == '/dashboard':
                    if not user_id:
                        self._redirect('/login')
                        return
                    
                    # 显示用户仪表盘
                    user_dashboard = dashboard.get_user_dashboard(user_id)
                    html = user_dashboard.generate_html_report()
                    # 添加用户菜单
                    html = dashboard._add_user_menu(html, user_id)
                    self._send_html(html)
                
                elif path == '/api/stats':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    
                    user_dashboard = dashboard.get_user_dashboard(user_id)
                    stats = user_dashboard.get_website_stats()
                    self._send_json(stats)
                
                elif path == '/api/user':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    
                    user = user_manager.get_user_by_id(user_id)
                    if user:
                        self._send_json({
                            'username': user.username,
                            'email': user.email,
                            'plan': user.plan,
                            'max_websites': user.max_websites,
                            'max_daily_visits': user.max_daily_visits,
                            'api_key': user.api_key
                        })
                    else:
                        self._send_json({'error': '用户不存在'}, 404)
                
                else:
                    self._send_html('<h1>404 - 页面不存在</h1>', 404)
            
            def do_POST(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path
                
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                params = parse_qs(post_data)
                
                if path == '/login':
                    username = params.get('username', [''])[0]
                    password = params.get('password', [''])[0]
                    
                    user = user_manager.login(username, password)
                    if user:
                        session_id = secrets.token_hex(16)
                        dashboard.sessions[session_id] = user.user_id
                        self._redirect('/dashboard', {'session_id': session_id})
                    else:
                        self._send_html(dashboard.generate_login_page('用户名或密码错误'))
                
                elif path == '/register':
                    username = params.get('username', [''])[0]
                    email = params.get('email', [''])[0]
                    password = params.get('password', [''])[0]
                    password_confirm = params.get('password_confirm', [''])[0]
                    
                    # 验证
                    if password != password_confirm:
                        self._send_html(dashboard.generate_register_page('两次输入的密码不一致'))
                        return
                    
                    if len(password) < 6:
                        self._send_html(dashboard.generate_register_page('密码长度至少6位'))
                        return
                    
                    user = user_manager.register(username, email, password)
                    if user:
                        session_id = secrets.token_hex(16)
                        dashboard.sessions[session_id] = user.user_id
                        self._redirect('/dashboard', {'session_id': session_id})
                    else:
                        self._send_html(dashboard.generate_register_page('用户名或邮箱已存在'))
                
                else:
                    self._send_html('<h1>404 - 页面不存在</h1>', 404)
            
            def _get_cookie(self, name: str) -> Optional[str]:
                """获取Cookie"""
                cookie_header = self.headers.get('Cookie', '')
                cookies = {}
                for cookie in cookie_header.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        cookies[key] = value
                return cookies.get(name)
            
            def _send_html(self, html: str, status: int = 200, cookies: dict = None):
                """发送HTML响应"""
                self.send_response(status)
                if cookies:
                    for name, value in cookies.items():
                        self.send_header('Set-Cookie', f'{name}={value}; Path=/; HttpOnly')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            
            def _send_json(self, data: dict, status: int = 200):
                """发送JSON响应"""
                self.send_response(status)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            
            def _redirect(self, location: str, cookies: dict = None):
                """重定向"""
                self.send_response(302)
                self.send_header('Location', location)
                if cookies:
                    for name, value in cookies.items():
                        self.send_header('Set-Cookie', f'{name}={value}; Path=/; HttpOnly')
                self.end_headers()
            
            def log_message(self, format, *args):
                logger.info(f"Dashboard: {args[0]}")
        
        import secrets
        self.server = HTTPServer(('0.0.0.0', self.port), MultiUserHandler)
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"📊 多用户仪表盘已启动: http://0.0.0.0:{self.port}")
    
    def _add_user_menu(self, html: str, user_id: str) -> str:
        """在HTML中添加用户菜单"""
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return html
        
        menu_html = f"""
        <div style="position: fixed; top: 20px; right: 20px; z-index: 1000;">
            <div style="background: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <span style="font-weight: 600; color: #333;">👤 {user.username}</span>
                <span style="background: #667eea; color: white; padding: 3px 10px; border-radius: 15px; font-size: 0.8em; margin-left: 10px;">{user.plan}</span>
                <br>
                <small style="color: #666;">API Key: {user.api_key[:20]}...</small>
                <br>
                <a href="/logout" style="color: #ef4444; text-decoration: none; font-size: 0.9em;">退出登录</a>
            </div>
        </div>
        """
        
        # 在<body>后插入菜单
        return html.replace('<body>', f'<body>{menu_html}')
    
    def stop_server(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            logger.info("📊 多用户仪表盘已停止")


# 全局实例
multi_user_dashboard = MultiUserDashboard()
