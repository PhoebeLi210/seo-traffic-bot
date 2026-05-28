"""
任务管理路由 - 处理任务相关的API请求
"""

import json
from typing import Dict, Any, Optional


class TaskHandler:
    """任务管理路由处理类"""

    def __init__(self, session_manager, task_service):
        """
        初始化任务处理器

        Args:
            session_manager: SessionManager实例
            task_service: TaskService实例
        """
        self._session_manager = session_manager
        self._task_service = task_service

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

    def handle_get_tasks(self, cookies: Dict[str, str], query_params: Dict = None) -> Dict[str, Any]:
        """
        处理GET任务列表请求

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
        keyword_filter = query_params.get('keyword', [''])[0].lower() if query_params.get('keyword') else ''
        engine_filter = query_params.get('engine', [''])[0] if query_params.get('engine') else ''
        status_filter = query_params.get('status', [''])[0] if query_params.get('status') else ''

        tasks = self._task_service.filter_tasks(
            user_id,
            keyword=keyword_filter,
            engine=engine_filter,
            status=status_filter
        )

        # 获取原始任务总数
        all_tasks = self._task_service.load_tasks(user_id)

        return {'tasks': tasks, 'total': len(all_tasks)}

    def handle_get_task_stats(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        """
        处理GET任务统计请求

        Args:
            cookies: 请求的cookies

        Returns:
            JSON响应
        """
        user_id = self.check_auth(cookies)
        if not user_id:
            return {'error': '未登录', 'status': 401}

        return self._task_service.get_task_stats(user_id)

    def handle_post_add_task(self, cookies: Dict[str, str], post_data: str) -> Dict[str, Any]:
        """
        处理POST添加任务请求

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
            data = json.loads(post_data) if isinstance(post_data, str) else post_data
            if not isinstance(data, dict):
                return {'error': '无效的数据格式', 'status': 400}
        except json.JSONDecodeError:
            return {'error': '无效的JSON格式', 'status': 400}

        task = self._task_service.create_task(user_id, data)
        if task:
            return {'success': True, 'task': task}
        else:
            return {'error': '创建任务失败', 'status': 500}

    def handle_post_toggle_task(self, cookies: Dict[str, str], post_data: str) -> Dict[str, Any]:
        """
        处理POST切换任务状态请求

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
            data = json.loads(post_data) if isinstance(post_data, str) else post_data
            task_id = data.get('task_id') if isinstance(data, dict) else None
            if not task_id:
                return {'error': '缺少task_id参数', 'status': 400}
        except json.JSONDecodeError:
            return {'error': '无效的JSON格式', 'status': 400}

        new_status = self._task_service.toggle_task(user_id, task_id)
        if new_status is not None:
            return {'success': True, 'status': new_status, 'task_id': task_id}
        else:
            return {'error': '任务不存在', 'status': 404}

    def handle_post_batch_action(self, cookies: Dict[str, str], post_data: str) -> Dict[str, Any]:
        """
        处理POST批量操作请求

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
            data = json.loads(post_data) if isinstance(post_data, str) else post_data
            action = data.get('action') if isinstance(data, dict) else None
            task_ids = data.get('task_ids', []) if isinstance(data, dict) else []

            if not action or not task_ids:
                return {'error': '缺少action或task_ids参数', 'status': 400}
        except json.JSONDecodeError:
            return {'error': '无效的JSON格式', 'status': 400}

        result = self._task_service.batch_update_tasks(user_id, task_ids, action)
        return {
            'success': True,
            'action': action,
            'success_count': result['success_count'],
            'failed_count': result['failed_count']
        }
