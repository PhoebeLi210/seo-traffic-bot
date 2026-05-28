"""
任务管理服务 - 处理任务数据的增删改查
"""

import json
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from user_manager import user_manager


class TaskService:
    """任务管理服务类"""

    def __init__(self):
        self._user_manager = user_manager

    def _get_tasks_file(self, user_id: str) -> Path:
        """获取用户任务文件路径"""
        return self._user_manager.get_user_data_dir(user_id) / "tasks.json"

    def load_tasks(self, user_id: str) -> List[Dict]:
        """
        从用户目录加载任务列表

        Args:
            user_id: 用户ID

        Returns:
            任务列表
        """
        f = self._get_tasks_file(user_id)
        if f.exists():
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    return json.load(fp).get('tasks', [])
            except Exception:
                return []
        return []

    def save_task(self, user_id: str, task: Dict) -> bool:
        """
        保存单个任务

        Args:
            user_id: 用户ID
            task: 任务数据

        Returns:
            是否保存成功
        """
        try:
            tasks = self.load_tasks(user_id)
            # 查找并更新或添加新任务
            found = False
            for i, t in enumerate(tasks):
                if t.get('task_id') == task.get('task_id'):
                    tasks[i] = task
                    found = True
                    break
            if not found:
                tasks.append(task)
            # 保存到文件
            f = self._get_tasks_file(user_id)
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump({'tasks': tasks}, fp, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def delete_task(self, user_id: str, task_id: str) -> bool:
        """
        删除单个任务

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        tasks = self.load_tasks(user_id)
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get('task_id') != task_id]
        if len(tasks) == original_len:
            return False
        f = self._get_tasks_file(user_id)
        with open(f, 'w', encoding='utf-8') as fp:
            json.dump({'tasks': tasks}, fp, ensure_ascii=False, indent=2)
        return True

    def toggle_task(self, user_id: str, task_id: str) -> Optional[str]:
        """
        切换任务状态

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            新的状态，如果任务不存在返回None
        """
        tasks = self.load_tasks(user_id)
        for task in tasks:
            if task.get('task_id') == task_id:
                new_status = 'paused' if task.get('status') == 'running' else 'running'
                task['status'] = new_status
                self.save_task(user_id, task)
                return new_status
        return None

    def get_task(self, user_id: str, task_id: str) -> Optional[Dict]:
        """
        获取单个任务

        Args:
            user_id: 用户ID
            task_id: 任务ID

        Returns:
            任务数据
        """
        tasks = self.load_tasks(user_id)
        for task in tasks:
            if task.get('task_id') == task_id:
                return task
        return None

    def get_task_stats(self, user_id: str) -> Dict:
        """
        获取任务统计

        Args:
            user_id: 用户ID

        Returns:
            任务统计字典
        """
        tasks = self.load_tasks(user_id)
        running_count = sum(1 for t in tasks if t.get('status') == 'running')
        paused_count = sum(1 for t in tasks if t.get('status') == 'paused')
        total_optimized = sum(t.get('total_optimized', 0) for t in tasks)
        daily_optimized = sum(t.get('daily_optimized', 0) for t in tasks)
        return {
            "total_tasks": len(tasks),
            "running_tasks": running_count,
            "paused_tasks": paused_count,
            "total_optimized": total_optimized,
            "daily_optimized": daily_optimized
        }

    def filter_tasks(self, user_id: str, keyword: str = '', engine: str = '', status: str = '') -> List[Dict]:
        """
        过滤任务

        Args:
            user_id: 用户ID
            keyword: 关键词过滤
            engine: 搜索引擎过滤
            status: 状态过滤

        Returns:
            过滤后的任务列表
        """
        tasks = self.load_tasks(user_id)
        filtered_tasks = []
        for task in tasks:
            if keyword and keyword.lower() not in task.get('keyword', '').lower():
                continue
            if engine and task.get('engine') != engine:
                continue
            if status and task.get('status') != status:
                continue
            filtered_tasks.append(task)
        return filtered_tasks

    def create_task(self, user_id: str, data: Dict) -> Optional[Dict]:
        """
        创建新任务

        Args:
            user_id: 用户ID
            data: 任务数据

        Returns:
            创建的任务数据
        """
        task = {
            'task_id': str(uuid.uuid4()),
            'keyword': data.get('keyword', ''),
            'url': data.get('url', ''),
            'engine': data.get('engine', 'baidu'),
            'initial_rank': data.get('initial_rank', 0),
            'current_rank': data.get('current_rank', 0),
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'daily_optimized': 0,
            'total_optimized': 0,
            'status': 'running',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        self.save_task(user_id, task)
        return task

    def batch_update_tasks(self, user_id: str, task_ids: List[str], action: str) -> Dict:
        """
        批量更新任务

        Args:
            user_id: 用户ID
            task_ids: 任务ID列表
            action: 操作类型 (start, pause, delete)

        Returns:
            操作结果统计
        """
        success_count = 0
        failed_count = 0

        if action == 'delete':
            for task_id in task_ids:
                if self.delete_task(user_id, task_id):
                    success_count += 1
                else:
                    failed_count += 1
        else:
            tasks = self.load_tasks(user_id)
            for task in tasks:
                if task.get('task_id') in task_ids:
                    if action == 'start':
                        task['status'] = 'running'
                    elif action == 'pause':
                        task['status'] = 'paused'
                    self.save_task(user_id, task)
                    success_count += 1

        return {
            'success_count': success_count,
            'failed_count': failed_count
        }


# 全局任务服务实例
task_service = TaskService()
