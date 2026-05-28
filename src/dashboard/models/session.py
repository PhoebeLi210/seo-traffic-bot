"""
Session模型 - 管理会话ID到用户ID的映射
"""

import secrets
from typing import Dict, Optional


class SessionManager:
    """简单的Session管理器"""

    def __init__(self):
        self._sessions: Dict[str, str] = {}  # session_id -> user_id

    def create_session(self, user_id: str) -> str:
        """
        创建新会话

        Args:
            user_id: 用户ID

        Returns:
            session_id: 新创建的会话ID
        """
        session_id = secrets.token_hex(16)
        self._sessions[session_id] = user_id
        return session_id

    def get_user_id(self, session_id: str) -> Optional[str]:
        """
        通过session_id获取用户ID

        Args:
            session_id: 会话ID

        Returns:
            user_id: 用户ID，如果会话不存在返回None
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功删除
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def is_valid_session(self, session_id: str) -> bool:
        """检查会话是否有效"""
        return session_id in self._sessions

    def clear_user_sessions(self, user_id: str) -> int:
        """
        清除用户的所有会话

        Args:
            user_id: 用户ID

        Returns:
            清除的会话数量
        """
        to_delete = [sid for sid, uid in self._sessions.items() if uid == user_id]
        for sid in to_delete:
            del self._sessions[sid]
        return len(to_delete)

    @property
    def session_count(self) -> int:
        """获取当前会话数量"""
        return len(self._sessions)


# 全局会话管理器实例
session_manager = SessionManager()
