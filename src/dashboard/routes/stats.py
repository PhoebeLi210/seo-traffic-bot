"""
统计路由 - 处理统计数据相关的API请求
"""

from typing import Dict, Any, Optional


class StatsHandler:
    """统计路由处理类"""

    def __init__(self, session_manager, stats_service):
        """
        初始化统计处理器

        Args:
            session_manager: SessionManager实例
            stats_service: StatsService实例
        """
        self._session_manager = session_manager
        self._stats_service = stats_service

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

    def handle_get_stats(self, cookies: Dict[str, str], query_params: Dict = None) -> Dict[str, Any]:
        """
        处理GET统计数据请求

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
        days = int(query_params.get('days', ['7'])[0]) if query_params.get('days') else 7

        # 限制天数范围
        if days not in [7, 30, 90]:
            days = 7

        stats = self._stats_service.get_stats(user_id, days=days)
        return stats

    def handle_get_trend_data(self, cookies: Dict[str, str], query_params: Dict = None) -> Dict[str, Any]:
        """
        处理GET趋势数据请求

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
        days = int(query_params.get('days', ['7'])[0]) if query_params.get('days') else 7
        metric = query_params.get('metric', ['visits'])[0] if query_params.get('metric') else 'visits'

        # 限制天数范围
        if days not in [7, 30, 90]:
            days = 7
        # 限制指标类型
        if metric not in ['visits', 'success_rate', 'rank']:
            metric = 'visits'

        trend_data = self._stats_service.get_trend_data(user_id, days=days, metric=metric)
        return trend_data
