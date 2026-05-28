"""
Google Search Console 关键词推荐模块
获取排名在 4-20 位的"冲刺距离"关键词
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class StrikingKeyword:
    """冲刺关键词数据"""
    keyword: str
    url: str
    position: float
    clicks: int
    impressions: int
    ctr: float
    potential: str  # 'high', 'medium', 'low' 基于排名位置


class GSCKeywordRecommender:
    """GSC关键词推荐器"""
    
    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path or "config/gsc_credentials.json"
        self._credentials = None
        self._service = None
        
    def _load_credentials(self) -> bool:
        """加载GSC凭证"""
        cred_file = Path(self.credentials_path)
        if not cred_file.exists():
            logger.warning(f"GSC凭证文件不存在: {self.credentials_path}")
            return False
        try:
            with open(cred_file, 'r', encoding='utf-8') as f:
                self._credentials = json.load(f)
            return True
        except Exception as e:
            logger.error(f"加载GSC凭证失败: {e}")
            return False
    
    def _get_service(self):
        """获取GSC API服务（延迟加载）"""
        if self._service:
            return self._service
            
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            
            if not self._load_credentials():
                return None
                
            # 支持服务账号和OAuth两种认证方式
            if 'type' in self._credentials and self._credentials['type'] == 'service_account':
                # 服务账号认证
                credentials = service_account.Credentials.from_service_account_info(
                    self._credentials,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
            else:
                # OAuth认证
                from google.oauth2.credentials import Credentials
                credentials = Credentials.from_authorized_user_info(
                    self._credentials,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
            
            self._service = build('webmasters', 'v3', credentials=credentials)
            return self._service
            
        except ImportError:
            logger.error("缺少Google API库，请安装: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return None
        except Exception as e:
            logger.error(f"初始化GSC服务失败: {e}")
            return None
    
    def get_striking_keywords(
        self, 
        site_url: str, 
        min_position: int = 4, 
        max_position: int = 20,
        days: int = 28,
        min_impressions: int = 10
    ) -> List[StrikingKeyword]:
        """
        获取冲刺距离关键词
        
        Args:
            site_url: 网站URL (如 https://example.com/)
            min_position: 最小排名位置 (默认4，即排除前3名)
            max_position: 最大排名位置 (默认20)
            days: 查询天数 (默认28天)
            min_impressions: 最小展示次数过滤
            
        Returns:
            冲刺关键词列表
        """
        service = self._get_service()
        if not service:
            logger.warning("GSC服务未初始化，返回模拟数据")
            return self._get_mock_keywords(site_url)
        
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # 调用GSC API获取查询数据
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query', 'page'],
                'rowLimit': 5000
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            keywords = []
            for row in response.get('rows', []):
                position = row.get('position', 0)
                impressions = row.get('impressions', 0)
                
                # 筛选排名在指定范围内的关键词
                if min_position <= position <= max_position and impressions >= min_impressions:
                    keyword = row['keys'][0]  # query
                    url = row['keys'][1] if len(row['keys']) > 1 else site_url  # page
                    
                    # 计算潜力等级
                    if position <= 10:
                        potential = 'high'  # 第1页，潜力最高
                    elif position <= 15:
                        potential = 'medium'  # 接近第1页
                    else:
                        potential = 'low'  # 较远
                    
                    keywords.append(StrikingKeyword(
                        keyword=keyword,
                        url=url,
                        position=round(position, 1),
                        clicks=row.get('clicks', 0),
                        impressions=impressions,
                        ctr=round(row.get('ctr', 0) * 100, 2),
                        potential=potential
                    ))
            
            # 按潜力等级和排名排序
            keywords.sort(key=lambda x: (
                {'high': 0, 'medium': 1, 'low': 2}[x.potential],
                x.position
            ))
            
            logger.info(f"从GSC获取到 {len(keywords)} 个冲刺关键词")
            return keywords
            
        except Exception as e:
            logger.error(f"获取GSC数据失败: {e}")
            return self._get_mock_keywords(site_url)
    
    def _get_mock_keywords(self, site_url: str) -> List[StrikingKeyword]:
        """获取模拟关键词（当GSC不可用时）"""
        # 从URL生成一些模拟关键词
        domain = site_url.replace('https://', '').replace('http://', '').replace('/', '')
        
        mock_keywords = [
            StrikingKeyword(f"{domain} 官网", site_url, 5.2, 120, 2300, 5.2, 'high'),
            StrikingKeyword(f"{domain} 登录", site_url, 7.8, 89, 1500, 5.9, 'high'),
            StrikingKeyword(f"{domain} 注册", site_url, 12.3, 45, 890, 5.1, 'medium'),
            StrikingKeyword(f"{domain} 下载", site_url, 15.6, 32, 650, 4.9, 'medium'),
            StrikingKeyword(f"{domain} 教程", site_url, 18.2, 28, 520, 5.4, 'low'),
        ]
        
        logger.info(f"返回 {len(mock_keywords)} 个模拟关键词")
        return mock_keywords
    
    def get_recommended_keywords_for_site(self, site_url: str, limit: int = 10) -> List[str]:
        """
        获取推荐关键词列表（仅返回关键词字符串）
        
        Args:
            site_url: 网站URL
            limit: 返回数量限制
            
        Returns:
            关键词字符串列表
        """
        striking = self.get_striking_keywords(site_url)
        return [k.keyword for k in striking[:limit]]
    
    def check_credentials_setup(self) -> Dict[str, Any]:
        """检查GSC凭证配置状态"""
        cred_file = Path(self.credentials_path)
        
        result = {
            'configured': False,
            'file_exists': cred_file.exists(),
            'file_path': str(cred_file.absolute()),
            'message': ''
        }
        
        if not cred_file.exists():
            result['message'] = '凭证文件不存在，请先配置GSC API凭证'
            return result
        
        try:
            with open(cred_file, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            
            if 'type' in creds and creds['type'] == 'service_account':
                result['configured'] = True
                result['message'] = '服务账号凭证已配置'
            elif 'refresh_token' in creds:
                result['configured'] = True
                result['message'] = 'OAuth凭证已配置'
            else:
                result['message'] = '凭证文件格式不正确'
                
        except Exception as e:
            result['message'] = f'凭证文件读取失败: {e}'
        
        return result


# 全局实例
gsc_recommender = GSCKeywordRecommender()


if __name__ == '__main__':
    # 测试代码
    recommender = GSCKeywordRecommender()
    
    # 检查凭证状态
    status = recommender.check_credentials_setup()
    print(f"凭证状态: {status}")
    
    # 获取推荐关键词
    keywords = recommender.get_recommended_keywords_for_site('https://example.com/')
    print(f"\n推荐关键词: {keywords}")
