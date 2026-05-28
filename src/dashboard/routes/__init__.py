"""
Routes包 - HTTP路由处理
"""

from .auth import AuthHandler
from .website import WebsiteHandler
from .task import TaskHandler
from .rank import RankHandler
from .stats import StatsHandler

__all__ = [
    'AuthHandler',
    'WebsiteHandler',
    'TaskHandler',
    'RankHandler',
    'StatsHandler',
]
