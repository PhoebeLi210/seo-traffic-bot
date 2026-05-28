"""
认证路由 - 处理登录、注册、登出
"""

import secrets
from typing import Dict, Any, Callable, Optional
from urllib.parse import parse_qs


class AuthHandler:
    """认证路由处理类"""

    def __init__(self, session_manager, user_service, template_renderer):
        """
        初始化认证处理器

        Args:
            session_manager: SessionManager实例
            user_service: UserService实例
            template_renderer: 模板渲染函数
        """
        self._session_manager = session_manager
        self._user_service = user_service
        self._render_template = template_renderer

    def handle_get_login(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理GET登录页面请求

        Args:
            cookies: 请求的cookies

        Returns:
            响应数据字典
        """
        # 如果已登录，重定向到仪表盘
        session_id = cookies.get('session_id')
        if session_id and self._session_manager.is_valid_session(session_id):
            return {'redirect': '/dashboard'}

        html = self._render_template('login.html')
        return {'html': html}

    def handle_get_register(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理GET注册页面请求

        Args:
            cookies: 请求的cookies

        Returns:
            响应数据字典
        """
        # 如果已登录，重定向到仪表盘
        session_id = cookies.get('session_id')
        if session_id and self._session_manager.is_valid_session(session_id):
            return {'redirect': '/dashboard'}

        html = self._render_template('register.html')
        return {'html': html}

    def handle_get_logout(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理GET登出请求

        Args:
            cookies: 请求的cookies

        Returns:
            响应数据字典
        """
        session_id = cookies.get('session_id')
        if session_id:
            self._session_manager.delete_session(session_id)
        return {'redirect': '/login', 'clear_cookie': 'session_id'}

    def handle_post_login(self, params: Dict, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理POST登录请求

        Args:
            params: 请求参数
            cookies: 请求的cookies

        Returns:
            响应数据字典
        """
        # 提取参数
        username = self._get_param(params, 'username')
        password = self._get_param(params, 'password')

        if not username or not password:
            return {
                'html': self._render_template('login.html', error='请输入用户名和密码'),
                'status': 400
            }

        user = self._user_service.login(username, password)
        if user:
            session_id = self._session_manager.create_session(user.user_id)
            return {
                'redirect': '/dashboard',
                'cookies': {'session_id': session_id}
            }
        else:
            return {
                'html': self._render_template('login.html', error='用户名或密码错误'),
                'status': 401
            }

    def handle_post_register(self, params: Dict) -> Dict[str, Any]:
        """
        处理POST注册请求

        Args:
            params: 请求参数

        Returns:
            响应数据字典
        """
        # 提取参数
        username = self._get_param(params, 'username')
        email = self._get_param(params, 'email')
        password = self._get_param(params, 'password')
        password_confirm = self._get_param(params, 'password_confirm')

        # 验证参数
        if not username or not email or not password:
            return {
                'html': self._render_template('register.html', error='请填写所有必填项'),
                'status': 400
            }

        if password != password_confirm:
            return {
                'html': self._render_template('register.html', error='两次输入的密码不一致'),
                'status': 400
            }

        if len(password) < 6:
            return {
                'html': self._render_template('register.html', error='密码长度至少6位'),
                'status': 400
            }

        user = self._user_service.register(username, email, password)
        if user:
            session_id = self._session_manager.create_session(user.user_id)
            return {
                'redirect': '/dashboard',
                'cookies': {'session_id': session_id}
            }
        else:
            return {
                'html': self._render_template('register.html', error='用户名或邮箱已存在'),
                'status': 400
            }

    def _get_param(self, params: Dict, key: str) -> Optional[str]:
        """从参数中获取值"""
        value = params.get(key)
        if isinstance(value, list):
            return value[0] if value else None
        return value
