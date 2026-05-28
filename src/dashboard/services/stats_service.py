"""
统计服务 - 处理统计数据和趋势数据
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from user_manager import user_manager


class StatsService:
    """统计服务类"""

    def __init__(self):
        self._user_manager = user_manager

    def _get_stats_dir(self, user_id: str) -> Path:
        """获取用户统计目录"""
        return self._user_manager.get_user_data_dir(user_id) / "stats"

    def get_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        获取用户统计数据

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            统计数据字典
        """
        stats_dir = self._get_stats_dir(user_id)
        total_visits = 0
        success_visits = 0
        failed_visits = 0
        website_summary = {}
        daily_data = []

        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            stats_file = stats_dir / f"{target_date.isoformat()}.json"
            if stats_file.exists():
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        daily_data.append(data)
                        total_visits += data.get("total_visits", 0)
                        success_visits += data.get("successful_visits", 0)
                        failed_visits += data.get("failed_visits", 0)
                        for url, site_data in data.get("websites", {}).items():
                            if url not in website_summary:
                                website_summary[url] = {"visits": 0, "success": 0, "failed": 0}
                            website_summary[url]["visits"] += site_data.get("total_visits", 0)
                            website_summary[url]["success"] += site_data.get("successful_visits", 0)
                            website_summary[url]["failed"] += site_data.get("failed_visits", 0)
                except Exception:
                    pass

        return {
            "total_visits": total_visits,
            "success_visits": success_visits,
            "failed_visits": failed_visits,
            "success_rate": (success_visits / total_visits * 100) if total_visits > 0 else 0,
            "website_summary": website_summary,
            "daily_data": daily_data,
            "days": days
        }

    def get_trend_data(self, user_id: str, days: int = 7, metric: str = 'visits') -> Dict:
        """
        获取指定时间范围和指标的趋势数据

        Args:
            user_id: 用户ID
            days: 天数 (7, 30, 90)
            metric: 指标类型 ('visits', 'success_rate', 'rank')

        Returns:
            {'labels': ['日期1', '日期2', ...], 'data': [值1, 值2, ...]}
        """
        stats_dir = self._get_stats_dir(user_id)
        labels = []
        data = []

        # 从最近一天往前遍历
        for i in range(days - 1, -1, -1):
            target_date = date.today() - timedelta(days=i)
            labels.append(target_date.strftime('%m-%d'))

            stats_file = stats_dir / f"{target_date.isoformat()}.json"
            if stats_file.exists():
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)

                    if metric == 'visits':
                        # 访问量
                        value = file_data.get("total_visits", 0)
                    elif metric == 'success_rate':
                        # 成功率
                        total = file_data.get("total_visits", 0)
                        success = file_data.get("successful_visits", 0)
                        value = (success / total * 100) if total > 0 else 0
                    elif metric == 'rank':
                        # 排名变化 - 从任务数据计算平均排名变化
                        value = 0
                    else:
                        value = 0

                    data.append(value)
                except Exception:
                    data.append(0)
            else:
                data.append(0)

        return {'labels': labels, 'data': data}

    def save_daily_stats(self, user_id: str, stats_data: Dict) -> bool:
        """
        保存每日统计数据

        Args:
            user_id: 用户ID
            stats_data: 统计数据

        Returns:
            是否保存成功
        """
        try:
            stats_dir = self._get_stats_dir(user_id)
            stats_dir.mkdir(parents=True, exist_ok=True)

            target_date = date.today().isoformat()
            stats_file = stats_dir / f"{target_date}.json"

            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_daily_stats(self, user_id: str, target_date: date = None) -> Dict:
        """
        获取指定日期的统计数据

        Args:
            user_id: 用户ID
            target_date: 目标日期，默认今天

        Returns:
            统计数据字典
        """
        if target_date is None:
            target_date = date.today()

        stats_dir = self._get_stats_dir(user_id)
        stats_file = stats_dir / f"{target_date.isoformat()}.json"

        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_website_stats(self, user_id: str, url: str, days: int = 7) -> Dict:
        """
        获取特定网站的统计数据

        Args:
            user_id: 用户ID
            url: 网站URL
            days: 统计天数

        Returns:
            网站统计数据
        """
        stats_dir = self._get_stats_dir(user_id)
        total_visits = 0
        success_visits = 0
        failed_visits = 0

        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            stats_file = stats_dir / f"{target_date.isoformat()}.json"
            if stats_file.exists():
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        website_data = data.get("websites", {}).get(url, {})
                        total_visits += website_data.get("total_visits", 0)
                        success_visits += website_data.get("successful_visits", 0)
                        failed_visits += website_data.get("failed_visits", 0)
                except Exception:
                    pass

        return {
            "url": url,
            "total_visits": total_visits,
            "success_visits": success_visits,
            "failed_visits": failed_visits,
            "success_rate": (success_visits / total_visits * 100) if total_visits > 0 else 0,
            "days": days
        }


# 全局统计服务实例
stats_service = StatsService()
