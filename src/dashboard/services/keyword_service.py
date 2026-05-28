"""
关键词推荐服务 - 处理百度指数关键词推荐
"""

import sys
import os
from typing import List, Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from baidu_index_recommender import baidu_recommender, KeywordRecommendation


class KeywordService:
    """关键词推荐服务类"""

    def __init__(self):
        self._recommender = baidu_recommender

    def get_recommendations(
        self,
        url: str,
        existing_keywords: List[str] = None,
        industry_hint: str = None,
        limit: int = 20
    ) -> List[KeywordRecommendation]:
        """
        获取关键词推荐

        Args:
            url: 网站URL
            existing_keywords: 已有关键词列表
            industry_hint: 行业提示（可选）
            limit: 返回数量限制

        Returns:
            关键词推荐列表
        """
        existing_keywords = existing_keywords or []
        return self._recommender.get_recommendations(
            url=url,
            existing_keywords=existing_keywords,
            industry_hint=industry_hint,
            limit=limit
        )

    def get_recommendations_dict(
        self,
        url: str,
        existing_keywords: List[str] = None,
        limit: int = 15
    ) -> Dict:
        """
        获取关键词推荐（字典格式）

        Args:
            url: 网站URL
            existing_keywords: 已有关键词列表
            limit: 返回数量限制

        Returns:
            包含success和recommendations的字典
        """
        recommendations = self.get_recommendations(url, existing_keywords, limit=limit)

        recs_data = []
        for rec in recommendations:
            recs_data.append({
                'keyword': rec.keyword,
                'category': rec.category,
                'search_volume': rec.search_volume,
                'competition': rec.competition,
                'trend': rec.trend,
                'relevance_score': rec.relevance_score,
                'reason': rec.reason
            })

        return {
            'success': True,
            'recommendations': recs_data,
            'message': f'找到 {len(recs_data)} 个推荐关键词'
        }

    def get_simple_recommendations(
        self,
        url: str,
        existing_keywords: List[str] = None,
        limit: int = 10
    ) -> List[str]:
        """
        获取简单推荐（仅返回关键词字符串）

        Args:
            url: 网站URL
            existing_keywords: 已有关键词
            limit: 数量限制

        Returns:
            关键词列表
        """
        return self._recommender.get_simple_recommendations(
            url=url,
            existing_keywords=existing_keywords,
            limit=limit
        )

    def analyze_keywords(self, keywords: List[str]) -> Dict:
        """
        分析关键词列表，提供优化建议

        Args:
            keywords: 关键词列表

        Returns:
            分析报告
        """
        return self._recommender.analyze_keywords(keywords)


# 全局关键词服务实例
keyword_service = KeywordService()
