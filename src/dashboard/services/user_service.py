"""
用户服务 - 封装用户相关的业务逻辑
"""

import sys
import os
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from user_manager import user_manager, User


class UserService:
    """用户服务类"""

    def __init__(self):
        self._user_manager = user_manager

    def login(self, username: str, password: str) -> Optional[User]:
        """
        用户登录

        Args:
            username: 用户名或邮箱
            password: 密码

        Returns:
            User对象，登录失败返回None
        """
        return self._user_manager.login(username, password)

    def register(self, username: str, email: str, password: str) -> Optional[User]:
        """
        注册用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码

        Returns:
            新用户对象，注册失败返回None
        """
        return self._user_manager.register(username, email, password)

    def get_user(self, user_id: str) -> Optional[User]:
        """
        获取用户

        Args:
            user_id: 用户ID

        Returns:
            User对象，不存在返回None
        """
        return self._user_manager.get_user_by_id(user_id)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """
        通过API密钥获取用户

        Args:
            api_key: API密钥

        Returns:
            User对象，不存在返回None
        """
        return self._user_manager.get_user_by_api_key(api_key)

    def regenerate_api_key(self, user_id: str) -> Optional[str]:
        """
        重新生成API密钥

        Args:
            user_id: 用户ID

        Returns:
            新API密钥
        """
        return self._user_manager.regenerate_api_key(user_id)

    def update_user_plan(self, user_id: str, plan: str, max_websites: int = None, max_daily_visits: int = None):
        """
        更新用户套餐

        Args:
            user_id: 用户ID
            plan: 套餐类型
            max_websites: 最大网站数量
            max_daily_visits: 最大每日访问次数
        """
        self._user_manager.update_user_plan(user_id, plan, max_websites, max_daily_visits)

    def list_all_users(self):
        """获取所有用户列表"""
        return self._user_manager.list_all_users()


# 全局用户服务实例
user_service = UserService()
