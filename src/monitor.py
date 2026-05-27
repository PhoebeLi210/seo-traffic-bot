"""
监控模块 - 记录访问日志和统计信息
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from loguru import logger

from .config_manager import config


@dataclass
class VisitRecord:
    """访问记录"""
    url: str
    success: bool
    start_time: str
    end_time: str
    duration: float
    error: str = ""
    pages_visited: int = 0
    proxy_used: bool = False


@dataclass
class DailyStats:
    """每日统计"""
    date: str
    total_visits: int = 0
    successful_visits: int = 0
    failed_visits: int = 0
    total_duration: float = 0
    average_duration: float = 0
    websites: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.websites is None:
            self.websites = {}


class Monitor:
    """监控器"""
    
    def __init__(self):
        self.monitoring_config = config.monitoring
        self.enabled = self.monitoring_config.enabled
        self.log_level = self.monitoring_config.log_level
        
        # 日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 统计数据目录
        self.stats_dir = Path("stats")
        self.stats_dir.mkdir(exist_ok=True)
        
        # 当日统计
        self.today_stats: DailyStats = self._load_today_stats()
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        log_file = self.monitoring_config.log_file or "logs/traffic_bot.log"
        
        logger.remove()
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            level=self.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        logger.add(
            lambda msg: print(msg, end=""),
            level="INFO",
            format="{time:HH:mm:ss} | {level} | {message}"
        )
    
    def _load_today_stats(self) -> DailyStats:
        """加载今日统计"""
        today = date.today().isoformat()
        stats_file = self.stats_dir / f"{today}.json"
        
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return DailyStats(**data)
            except Exception as e:
                logger.error(f"加载统计数据失败: {e}")
        
        return DailyStats(date=today)
    
    def _save_today_stats(self):
        """保存今日统计"""
        stats_file = self.stats_dir / f"{self.today_stats.date}.json"
        
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.today_stats), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存统计数据失败: {e}")
    
    def record_visit(self, result: Dict[str, Any]):
        """
        记录一次访问
        
        Args:
            result: 访问结果字典
        """
        if not self.enabled:
            return
        
        # 检查日期是否变化
        today = date.today().isoformat()
        if today != self.today_stats.date:
            self._save_today_stats()
            self.today_stats = DailyStats(date=today)
        
        # 更新统计
        self.today_stats.total_visits += 1
        
        if result.get("success"):
            self.today_stats.successful_visits += 1
        else:
            self.today_stats.failed_visits += 1
        
        duration = result.get("duration", 0)
        self.today_stats.total_duration += duration
        
        if self.today_stats.total_visits > 0:
            self.today_stats.average_duration = (
                self.today_stats.total_duration / self.today_stats.total_visits
            )
        
        # 更新网站统计
        url = result.get("url", "unknown")
        if url not in self.today_stats.websites:
            self.today_stats.websites[url] = {
                "total_visits": 0,
                "successful_visits": 0,
                "failed_visits": 0,
                "total_duration": 0
            }
        
        site_stats = self.today_stats.websites[url]
        site_stats["total_visits"] += 1
        
        if result.get("success"):
            site_stats["successful_visits"] += 1
        else:
            site_stats["failed_visits"] += 1
        
        site_stats["total_duration"] += duration
        
        # 保存统计
        self._save_today_stats()
        
        # 记录日志
        if result.get("success"):
            logger.info(
                f"✅ 访问成功: {url[:50]}... | "
                f"耗时: {duration:.1f}s | "
                f"页面: {result.get('pages_visited', 0)}"
            )
        else:
            logger.error(
                f"❌ 访问失败: {url[:50]}... | "
                f"错误: {result.get('error', '未知错误')[:100]}"
            )
    
    def get_stats(self, target_date: date = None) -> DailyStats:
        """
        获取指定日期的统计
        
        Args:
            target_date: 目标日期，默认为今天
            
        Returns:
            每日统计
        """
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.isoformat()
        
        if date_str == self.today_stats.date:
            return self.today_stats
        
        stats_file = self.stats_dir / f"{date_str}.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return DailyStats(**data)
            except Exception as e:
                logger.error(f"加载统计数据失败: {e}")
        
        return DailyStats(date=date_str)
    
    def print_summary(self):
        """打印今日统计摘要"""
        stats = self.today_stats
        
        print("\n" + "=" * 60)
        print(f"📊 今日访问统计 ({stats.date})")
        print("=" * 60)
        print(f"总访问次数: {stats.total_visits}")
        print(f"成功: {stats.successful_visits} | 失败: {stats.failed_visits}")
        
        if stats.total_visits > 0:
            success_rate = (stats.successful_visits / stats.total_visits) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print(f"总停留时间: {stats.total_duration / 60:.1f} 分钟")
        print(f"平均停留时间: {stats.average_duration:.1f} 秒")
        
        if stats.websites:
            print("\n各网站访问情况:")
            for url, site_stats in stats.websites.items():
                success = site_stats["successful_visits"]
                total = site_stats["total_visits"]
                rate = (success / total * 100) if total > 0 else 0
                print(f"  - {url[:40]}...: {success}/{total} ({rate:.0f}%)")
        
        print("=" * 60 + "\n")


# 全局监控器实例
monitor = Monitor()
