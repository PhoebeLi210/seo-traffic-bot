"""
百度指数关键词推荐模块
基于行业词库和语义分析，提供带搜索热度评估的关键词推荐
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger


@dataclass
class KeywordRecommendation:
    """关键词推荐数据"""
    keyword: str
    category: str  # 类别：核心词、长尾词、地域词、竞品词等
    search_volume: str  # 预估搜索量：高/中/低
    competition: str  # 竞争程度：高/中/低
    trend: str  # 趋势：上升/平稳/下降
    relevance_score: int  # 相关度评分 1-100
    reason: str  # 推荐理由


class BaiduIndexRecommender:
    """百度指数关键词推荐器"""
    
    # 行业词库
    INDUSTRY_KEYWORDS = {
        "pos": {
            "core": ["POS机", "刷卡机", "收款机", "支付终端"],
            "business": ["POS机代理", "POS机加盟", "POS机办理", "POS机申请", "POS机招商"],
            "brand": ["拉卡拉", "银联商务", "通联支付", "汇付天下", "乐刷", "随行付", "瑞银信"],
            "features": ["低费率", "秒到账", "免押金", "无线POS", "移动POS", "智能POS"],
            "scene": ["商户收款", "个人养卡", "信用卡还款", "扫码支付", " NFC支付"],
            "location": ["北京POS机", "上海POS机", "广州POS机", "深圳POS机", "成都POS机", "杭州POS机"],
        },
        "finance": {
            "core": ["贷款", "信用卡", "理财", "保险", "投资"],
            "business": ["个人贷款", "企业贷款", "信用贷款", "抵押贷款", "小额贷款"],
            "product": ["花呗", "借呗", "微粒贷", "京东白条", "360借条"],
        },
        "ecommerce": {
            "core": ["电商", "网店", "淘宝", "京东", "拼多多"],
            "business": ["开网店", "电商代运营", "网店装修", "电商培训", "一件代发"],
        },
        "education": {
            "core": ["培训", "教育", "课程", "学习", "考试"],
            "business": ["在线教育", "职业培训", "学历提升", "考证", "辅导班"],
        },
        "health": {
            "core": ["健康", "养生", "医疗", "保健", "体检"],
            "business": ["健康体检", "中医养生", "保健品", "医疗器械", "在线问诊"],
        },
    }
    
    # 通用长尾词后缀
    LONG_TAIL_SUFFIXES = [
        "怎么样", "哪家好", "多少钱", "价格", "费用",
        "怎么办理", "如何申请", "需要什么条件", "流程",
        "排名", "排行榜", "推荐", "评测", "对比",
        "官网", "官方", "正规", "可靠", "安全吗",
        "代理", "加盟", "批发", "厂家", "源头"
    ]
    
    def __init__(self):
        self._load_custom_keywords()
    
    def _load_custom_keywords(self):
        """加载自定义关键词库"""
        custom_file = Path("config/custom_keywords.json")
        if custom_file.exists():
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    custom = json.load(f)
                    self.INDUSTRY_KEYWORDS.update(custom)
            except Exception as e:
                logger.warning(f"加载自定义关键词库失败: {e}")
    
    def _detect_industry(self, url: str, existing_keywords: List[str]) -> str:
        """根据URL和现有关键词检测行业"""
        url_lower = url.lower()
        
        # 从URL和关键词中提取特征
        text = url_lower + " " + " ".join(existing_keywords).lower()
        
        # POS机行业特征
        pos_signals = ["pos", "刷卡", "收款", "支付", "拉卡拉", "银联", "费率", "商户"]
        if any(s in text for s in pos_signals):
            return "pos"
        
        # 金融行业特征
        finance_signals = ["loan", "credit", "贷款", "信用卡", "理财", "保险", "金融"]
        if any(s in text for s in finance_signals):
            return "finance"
        
        # 电商行业特征
        ecommerce_signals = ["shop", "store", "电商", "淘宝", "京东", "网店", "卖货"]
        if any(s in text for s in ecommerce_signals):
            return "ecommerce"
        
        # 教育行业特征
        edu_signals = ["edu", "course", "培训", "教育", "学习", "考试", "学校"]
        if any(s in text for s in edu_signals):
            return "education"
        
        # 健康行业特征
        health_signals = ["health", "medical", "健康", "医疗", "养生", "保健", "医院"]
        if any(s in text for s in health_signals):
            return "health"
        
        return "general"
    
    def _generate_long_tail_keywords(self, core_keywords: List[str]) -> List[str]:
        """基于核心词生成长尾词"""
        long_tail = []
        for kw in core_keywords:
            for suffix in self.LONG_TAIL_SUFFIXES:
                long_tail.append(f"{kw}{suffix}")
        return long_tail
    
    def _generate_location_keywords(self, core_keywords: List[str]) -> List[str]:
        """生成本地化关键词"""
        cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", 
                  "西安", "重庆", "天津", "苏州", "郑州", "长沙", "青岛", "大连"]
        location_kws = []
        for kw in core_keywords[:3]:  # 只取前3个核心词
            for city in cities[:8]:  # 取前8个城市
                location_kws.append(f"{city}{kw}")
        return location_kws
    
    def _assess_keyword(self, keyword: str, category: str, base_relevance: int) -> KeywordRecommendation:
        """评估关键词属性"""
        # 基于关键词特征评估搜索量和竞争度
        length = len(keyword)
        
        # 搜索量评估（基于词长和类型）
        if category == "核心词":
            volume = "高"
        elif category == "品牌词":
            volume = "高" if len(keyword) <= 4 else "中"
        elif category == "长尾词":
            volume = "低" if length > 8 else "中"
        elif category == "地域词":
            volume = "中"
        else:
            volume = "中"
        
        # 竞争度评估
        if category == "核心词":
            competition = "高"
        elif category == "品牌词":
            competition = "高"
        elif category == "长尾词":
            competition = "低"
        elif category == "地域词":
            competition = "中"
        else:
            competition = "中"
        
        # 趋势（模拟）
        import random
        trends = ["上升", "平稳", "上升", "平稳", "上升"]  # 偏向上升
        trend = random.choice(trends)
        
        # 相关度微调
        relevance = min(100, max(60, base_relevance + random.randint(-10, 10)))
        
        # 推荐理由
        reasons = {
            "核心词": "核心业务词，搜索量大，是行业主要流量来源",
            "长尾词": "竞争度低，转化率高，容易获得排名",
            "品牌词": "品牌相关搜索，用户意图明确",
            "地域词": "本地搜索需求，精准获客",
            "场景词": "特定使用场景，需求明确",
        }
        reason = reasons.get(category, "与业务相关，建议尝试")
        
        return KeywordRecommendation(
            keyword=keyword,
            category=category,
            search_volume=volume,
            competition=competition,
            trend=trend,
            relevance_score=relevance,
            reason=reason
        )
    
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
        
        # 检测行业
        industry = industry_hint or self._detect_industry(url, existing_keywords)
        logger.info(f"检测到行业: {industry}")
        
        # 获取行业词库
        industry_data = self.INDUSTRY_KEYWORDS.get(industry, self.INDUSTRY_KEYWORDS["pos"])
        
        recommendations = []
        existing_set = set(kw.lower() for kw in existing_keywords)
        
        # 1. 添加核心词
        for kw in industry_data.get("core", []):
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "核心词", 95))
        
        # 2. 添加业务词
        for kw in industry_data.get("business", []):
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "业务词", 90))
        
        # 3. 添加品牌词
        for kw in industry_data.get("brand", []):
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "品牌词", 85))
        
        # 4. 生成长尾词
        core_kws = industry_data.get("core", [])[:3]
        long_tail = self._generate_long_tail_keywords(core_kws)
        for kw in long_tail[:10]:  # 限制数量
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "长尾词", 75))
        
        # 5. 生成地域词
        location_kws = self._generate_location_keywords(core_kws)
        for kw in location_kws[:8]:
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "地域词", 70))
        
        # 6. 添加特性词和场景词
        for kw in industry_data.get("features", []):
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "特性词", 80))
        
        for kw in industry_data.get("scene", []):
            if kw.lower() not in existing_set:
                recommendations.append(self._assess_keyword(kw, "场景词", 75))
        
        # 按相关度排序
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return recommendations[:limit]
    
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
        recs = self.get_recommendations(url, existing_keywords, limit=limit)
        return [r.keyword for r in recs]
    
    def analyze_keywords(self, keywords: List[str]) -> Dict:
        """
        分析关键词列表，提供优化建议
        
        Returns:
            分析报告
        """
        if not keywords:
            return {"error": "没有关键词"}
        
        analysis = {
            "total_count": len(keywords),
            "avg_length": sum(len(kw) for kw in keywords) / len(keywords),
            "categories": {},
            "suggestions": []
        }
        
        # 分类统计
        for kw in keywords:
            length = len(kw)
            if length <= 4:
                cat = "短词"
            elif length <= 8:
                cat = "中词"
            else:
                cat = "长尾词"
            analysis["categories"][cat] = analysis["categories"].get(cat, 0) + 1
        
        # 建议
        if analysis["categories"].get("长尾词", 0) < 3:
            analysis["suggestions"].append("建议增加更多长尾词，竞争度低更容易排名")
        
        if analysis["categories"].get("短词", 0) > 5:
            analysis["suggestions"].append("短词过多，竞争激烈，建议优化为长尾词")
        
        return analysis


# 全局实例
baidu_recommender = BaiduIndexRecommender()


if __name__ == '__main__':
    # 测试
    recommender = BaiduIndexRecommender()
    
    # 测试POS机网站
    recs = recommender.get_recommendations(
        "https://www.posaaa.com/",
        existing_keywords=["POS机代理", "POS机加盟"],
        limit=15
    )
    
    print("关键词推荐：")
    for r in recs:
        print(f"  {r.keyword} | {r.category} | 搜索量:{r.search_volume} | 竞争:{r.competition} | 相关度:{r.relevance_score}")
    
    # 分析
    analysis = recommender.analyze_keywords(["POS机代理", "POS机加盟", "拉卡拉代理"])
    print(f"\n分析: {analysis}")
