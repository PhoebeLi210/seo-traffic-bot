"""
网站管理服务 - 处理网站数据的增删改查
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from user_manager import user_manager


class WebsiteService:
    """网站管理服务类"""

    def __init__(self):
        self._user_manager = user_manager

    def _get_websites_file(self, user_id: str) -> Path:
        """获取用户网站配置文件路径"""
        return self._user_manager.get_user_data_dir(user_id) / "config" / "websites.json"

    def load_websites(self, user_id: str) -> List[Dict]:
        """
        加载用户的网站列表

        Args:
            user_id: 用户ID

        Returns:
            网站列表
        """
        f = self._get_websites_file(user_id)
        if f.exists():
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    return json.load(fp).get('websites', [])
            except Exception:
                return []
        return []

    def save_websites(self, user_id: str, websites: List[Dict]) -> bool:
        """
        保存用户的网站列表

        Args:
            user_id: 用户ID
            websites: 网站列表

        Returns:
            是否保存成功
        """
        try:
            f = self._get_websites_file(user_id)
            f.parent.mkdir(parents=True, exist_ok=True)
            with open(f, 'w', encoding='utf-8') as fp:
                json.dump({'websites': websites}, fp, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_website_by_url(self, user_id: str, url: str) -> Optional[Dict]:
        """
        通过URL获取网站

        Args:
            user_id: 用户ID
            url: 网站URL

        Returns:
            网站数据字典
        """
        websites = self.load_websites(user_id)
        for ws in websites:
            if ws.get('url') == url:
                return ws
        return None

    def add_website(self, user_id: str, website: Dict) -> bool:
        """
        添加网站

        Args:
            user_id: 用户ID
            website: 网站数据

        Returns:
            是否添加成功
        """
        websites = self.load_websites(user_id)
        websites.append(website)
        return self.save_websites(user_id, websites)

    def update_website(self, user_id: str, index: int, website: Dict) -> bool:
        """
        更新网站

        Args:
            user_id: 用户ID
            index: 网站索引
            website: 新的网站数据

        Returns:
            是否更新成功
        """
        websites = self.load_websites(user_id)
        if 0 <= index < len(websites):
            websites[index] = website
            return self.save_websites(user_id, websites)
        return False

    def delete_website(self, user_id: str, index: int) -> bool:
        """
        删除网站

        Args:
            user_id: 用户ID
            index: 网站索引

        Returns:
            是否删除成功
        """
        websites = self.load_websites(user_id)
        if 0 <= index < len(websites):
            websites.pop(index)
            return self.save_websites(user_id, websites)
        return False

    def get_website_count(self, user_id: str) -> int:
        """获取用户网站数量"""
        return len(self.load_websites(user_id))

    def can_add_website(self, user_id: str, max_websites: int) -> bool:
        """检查是否可以添加更多网站"""
        return self.get_website_count(user_id) < max_websites


# 全局网站服务实例
website_service = WebsiteService()
