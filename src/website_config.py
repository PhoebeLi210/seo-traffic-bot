"""
网站配置扩展 - 支持定时和时间段设置
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class WebsiteConfig:
    """网站配置"""
    url: str
    name: str = ""
    enabled: bool = True
    keywords: List[str] = field(default_factory=list)
    click_count: int = 5
    
    # 时间段设置
    time_ranges: List[Dict] = field(default_factory=list)
    # 示例: [{"start": "09:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}]
    
    # 运行间隔（秒）
    run_interval: int = 3600  # 默认1小时
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WebsiteConfig':
        """从字典创建"""
        return cls(**data)
    
    def get_time_ranges_display(self) -> str:
        """获取时间段显示文本"""
        if not self.time_ranges:
            return "全天"
        
        ranges = []
        for r in self.time_ranges:
            ranges.append(f"{r['start']}-{r['end']}")
        return ", ".join(ranges)


# 预设时间段模板
TIME_RANGE_TEMPLATES = {
    'morning': {'name': '上午', 'ranges': [{'start': '09:00', 'end': '12:00'}]},
    'afternoon': {'name': '下午', 'ranges': [{'start': '14:00', 'end': '18:00'}]},
    'evening': {'name': '晚上', 'ranges': [{'start': '19:00', 'end': '22:00'}]},
    'workday': {'name': '工作日', 'ranges': [{'start': '09:00', 'end': '18:00'}]},
    'morning_afternoon': {'name': '上午+下午', 'ranges': [
        {'start': '09:00', 'end': '12:00'},
        {'start': '14:00', 'end': '18:00'}
    ]},
    'allday': {'name': '全天', 'ranges': []},
}


def apply_time_template(template_key: str) -> List[Dict]:
    """应用时间段模板"""
    template = TIME_RANGE_TEMPLATES.get(template_key)
    if template:
        return template['ranges']
    return []