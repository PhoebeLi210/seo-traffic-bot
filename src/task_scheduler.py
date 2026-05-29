"""
任务调度器 - 支持定时任务和时间段控制
"""

import asyncio
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class TimeRange:
    """时间段配置"""
    start: str  # 格式: "HH:MM"
    end: str    # 格式: "HH:MM"
    
    def is_in_range(self, current_time: dt_time = None) -> bool:
        """检查当前时间是否在范围内"""
        if current_time is None:
            current_time = datetime.now().time()
        
        start_hour, start_min = map(int, self.start.split(':'))
        end_hour, end_min = map(int, self.end.split(':'))
        
        start_time = dt_time(start_hour, start_min)
        end_time = dt_time(end_hour, end_min)
        
        return start_time <= current_time <= end_time


@dataclass
class ScheduledTask:
    """定时任务"""
    task_id: str
    name: str
    website_id: str
    keywords: List[str]
    click_count: int = 5
    time_ranges: List[TimeRange] = field(default_factory=list)
    enabled: bool = True
    last_run: float = 0
    run_interval: int = 3600  # 默认每小时运行一次
    
    def should_run_now(self) -> bool:
        """检查是否应该现在运行"""
        if not self.enabled:
            return False
        
        # 检查是否在允许的时间段内
        if self.time_ranges:
            in_range = any(r.is_in_range() for r in self.time_ranges)
            if not in_range:
                return False
        
        # 检查是否到了运行间隔
        if time.time() - self.last_run < self.run_interval:
            return False
        
        return True


class TaskScheduler:
    """任务调度器"""
    
    # 预设时间段模板
    TIME_TEMPLATES = {
        'morning': TimeRange("09:00", "12:00"),      # 上午
        'afternoon': TimeRange("14:00", "18:00"),    # 下午
        'evening': TimeRange("19:00", "22:00"),      # 晚上
        'workday': TimeRange("09:00", "18:00"),      # 工作日
        'allday': TimeRange("00:00", "23:59"),       # 全天
    }
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._callback: Optional[Callable] = None
    
    def add_task(self, task: ScheduledTask) -> bool:
        """添加定时任务"""
        self.tasks[task.task_id] = task
        logger.info(f"✅ 添加定时任务: {task.name} ({task.task_id})")
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除定时任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"🗑️ 移除定时任务: {task_id}")
            return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            return True
        return False
    
    def set_callback(self, callback: Callable):
        """设置任务执行回调函数"""
        self._callback = callback
    
    async def run(self):
        """运行调度器"""
        self._running = True
        logger.info("⏰ 任务调度器已启动")
        
        while self._running:
            try:
                current_time = datetime.now().strftime("%H:%M")
                
                for task_id, task in self.tasks.items():
                    if task.should_run_now():
                        logger.info(f"🚀 执行任务: {task.name} (当前时间: {current_time})")
                        
                        if self._callback:
                            try:
                                await self._callback(task)
                                task.last_run = time.time()
                            except Exception as e:
                                logger.error(f"❌ 任务执行失败 {task.name}: {e}")
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ 调度器错误: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("⏹️ 任务调度器已停止")
    
    def get_active_tasks(self) -> List[ScheduledTask]:
        """获取当前应该运行的任务"""
        return [t for t in self.tasks.values() if t.should_run_now()]
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务信息"""
        result = []
        for task in self.tasks.values():
            result.append({
                'task_id': task.task_id,
                'name': task.name,
                'enabled': task.enabled,
                'time_ranges': [f"{r.start}-{r.end}" for r in task.time_ranges],
                'next_run': self._calculate_next_run(task),
            })
        return result
    
    def _calculate_next_run(self, task: ScheduledTask) -> str:
        """计算下次运行时间"""
        if not task.enabled:
            return "已禁用"
        
        now = datetime.now()
        
        # 找到下一个在时间段内的时间点
        for r in task.time_ranges:
            start_hour, start_min = map(int, r.start.split(':'))
            start_time = now.replace(hour=start_hour, minute=start_min, second=0)
            
            if start_time > now:
                return start_time.strftime("%Y-%m-%d %H:%M")
        
        # 如果没有找到，说明是明天
        if task.time_ranges:
            r = task.time_ranges[0]
            start_hour, start_min = map(int, r.start.split(':'))
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=start_hour, minute=start_min).strftime("%Y-%m-%d %H:%M")
        
        return "未知"


# 全局调度器实例
task_scheduler = TaskScheduler()