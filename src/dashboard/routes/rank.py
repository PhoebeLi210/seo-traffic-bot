"""
排名查询路由 - 处理排名查询相关的API请求
"""

from typing import Dict, Any, Optional
from urllib.parse import parse_qs


class RankHandler:
    """排名查询路由处理类"""

    def __init__(self, session_manager, rank_service, keyword_service):
        """
        初始化排名查询处理器

        Args:
            session_manager: SessionManager实例
            rank_service: RankService实例
            keyword_service: KeywordService实例
        """
        self._session_manager = session_manager
        self._rank_service = rank_service
        self._keyword_service = keyword_service

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

    def handle_get_rank(self, cookies: Dict[str, str], query_params: Dict = None) -> Dict[str, Any]:
        """
        处理GET排名查询请求

        Args:
            cookies: 请求的cookies
            query_params: 查询参数

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        query_params = query_params or {}
        engine = query_params.get('engine', [''])[0] if query_params.get('engine') else ''
        keyword = query_params.get('keyword', [''])[0] if query_params.get('keyword') else ''
        domain = query_params.get('domain', [''])[0] if query_params.get('domain') else ''
        device = query_params.get('device', ['pc'])[0] if query_params.get('device') else 'pc'

        if not engine or not keyword or not domain:
            return {'error': '缺少必要参数 (engine, keyword, domain)', 'status': 400}

        result = self._rank_service.check_rank(keyword, domain, engine, device)
        return result

    def handle_get_baidu_recommend(self, cookies: Dict[str, str], query_params: Dict = None) -> Dict[str, Any]:
        """
        处理GET百度指数关键词推荐请求

        Args:
            cookies: 请求的cookies
            query_params: 查询参数

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        query_params = query_params or {}
        url = query_params.get('url', [''])[0] if query_params.get('url') else ''
        existing = query_params.get('existing', [''])[0] if query_params.get('existing') else ''

        if not url:
            return {'error': '缺少网站URL参数', 'status': 400}

        # 解析已有关键词
        existing_keywords = [kw.strip() for kw in existing.split(',') if kw.strip()]

        # 获取百度指数推荐
        result = self._keyword_service.get_recommendations_dict(
            url=url,
            existing_keywords=existing_keywords,
            limit=15
        )

        return result

    def handle_get_supported_engines(self) -> Dict[str, Any]:
        """
        处理获取支持的搜索引擎列表请求

        Returns:
            JSON响应
        """
        return {'engines': self._rank_service.get_supported_engines()}
