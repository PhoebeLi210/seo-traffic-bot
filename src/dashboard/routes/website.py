"""
网站管理路由 - 处理网站相关的API请求
"""

import json
from typing import Dict, Any, Optional


class WebsiteHandler:
    """网站管理路由处理类"""

    def __init__(self, session_manager, website_service, user_service):
        """
        初始化网站处理器

        Args:
            session_manager: SessionManager实例
            website_service: WebsiteService实例
            user_service: UserService实例
        """
        self._session_manager = session_manager
        self._website_service = website_service
        self._user_service = user_service

    def check_auth(self, cookies: Dict[str, str]) -> Optional[str]:
        """
        检查用户认证

        Args:
            cookies: 请求的cookies

        Returns:
            user_id 如果已登录，否则 None
        """
        session_id = cookies.get('session_id')
        if not session_id:
            return None
        return self._session_manager.get_user_id(session_id)

    def handle_get_websites(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理GET网站列表请求

        Args:
            cookies: 请求的cookies

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        websites = self._website_service.load_websites(user_id)
        return {'websites': websites}

    def handle_post_websites(self, cookies: Dict[str, str], post_data: str) -> Dict[str, Any]:
        """
        处理POST保存网站列表请求

        Args:
            cookies: 请求的cookies
            post_data: POST数据

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        try:
            data = json.loads(post_data)
            if isinstance(data, dict) and 'websites' in data:
                websites = data['websites']
            elif isinstance(data, list):
                websites = data
            else:
                return {'error': '无效的数据格式', 'status': 400}
        except json.JSONDecodeError:
            return {'error': '无效的JSON格式', 'status': 400}

        # 验证网站数量限制
        user = self._user_service.get_user(user_id)
        if user and len(websites) > user.max_websites:
            return {
                'error': f'网站数量超过限制 (最大 {user.max_websites})',
                'status': 400
            }

        if self._website_service.save_websites(user_id, websites):
            return {'success': True, 'message': '保存成功'}
        else:
            return {'error': '保存失败', 'status': 500}

    def handle_get_user_info(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理获取用户信息请求

        Args:
            cookies: 请求的cookies

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        user = self._user_service.get_user(user_id)
        if user:
            return {
                'username': user.username,
                'email': user.email,
                'plan': user.plan,
                'max_websites': user.max_websites,
                'max_daily_visits': user.max_daily_visits,
                'api_key': user.api_key
            }
        else:
            return {'error': '用户不存在', 'status': 404}
