"""
配置管理模块 - 统一管理所有配置文件
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class WebsiteConfig(BaseModel):
    """网站配置模型"""
    url: str
    name: str = ""
    enabled: bool = True
    keywords: List[str] = Field(default_factory=list)
    max_daily_visits: int = 15


class BrowserConfig(BaseModel):
    """浏览器配置模型"""
    headless: bool = True
    timeout: int = 30000
    viewport: Dict[str, int] = Field(default_factory=dict)
    user_agents: List[str] = Field(default_factory=list)


class BehaviorConfig(BaseModel):
    """行为模拟配置模型"""
    min_stay_duration: int = 10
    max_stay_duration: int = 30
    min_visit_interval: int = 120
    max_visit_interval: int = 300
    scroll: Dict[str, Any] = Field(default_factory=dict)
    mouse_move: Dict[str, Any] = Field(default_factory=dict)
    click: Dict[str, Any] = Field(default_factory=dict)


class ProxyConfig(BaseModel):
    """代理配置模型"""
    enabled: bool = True
    api_url: str = "http://127.0.0.1:5010/get"
    fallback_to_direct: bool = True
    test_url: str = "http://httpbin.org/ip"
    timeout: int = 10


class SchedulerConfig(BaseModel):
    """调度配置模型"""
    enabled: bool = True
    active_hours: Dict[str, int] = Field(default_factory=dict)
    run_on_weekends: bool = True


class MonitoringConfig(BaseModel):
    """监控配置模型"""
    enabled: bool = True
    log_level: str = "INFO"
    save_screenshots: bool = False
    track_metrics: bool = True


class Settings(BaseModel):
    """完整配置模型"""
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.websites_file = self.config_dir / "websites.json"
        self.settings_file = self.config_dir / "settings.yaml"
        
        self._websites: List[WebsiteConfig] = []
        self._settings: Settings = Settings()
        
        self._load_configs()
    
    def _load_configs(self):
        """加载所有配置文件"""
        self._load_websites()
        self._load_settings()
    
    def _load_websites(self):
        """加载网站配置"""
        if self.websites_file.exists():
            try:
                with open(self.websites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    websites_data = data.get('websites', [])
                    self._websites = [WebsiteConfig(**site) for site in websites_data]
            except Exception as e:
                print(f"加载网站配置失败: {e}")
                self._websites = []
    
    def _load_settings(self):
        """加载设置配置"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._settings = Settings(**data)
            except Exception as e:
                print(f"加载设置配置失败: {e}")
                self._settings = Settings()
    
    @property
    def websites(self) -> List[WebsiteConfig]:
        """获取所有启用的网站"""
        return [site for site in self._websites if site.enabled]
    
    @property
    def all_websites(self) -> List[WebsiteConfig]:
        """获取所有网站（包括禁用的）"""
        return self._websites
    
    @property
    def settings(self) -> Settings:
        """获取设置配置"""
        return self._settings
    
    @property
    def browser(self) -> BrowserConfig:
        """获取浏览器配置"""
        return self._settings.browser
    
    @property
    def behavior(self) -> BehaviorConfig:
        """获取行为配置"""
        return self._settings.behavior
    
    @property
    def proxy(self) -> ProxyConfig:
        """获取代理配置"""
        return self._settings.proxy
    
    @property
    def scheduler(self) -> SchedulerConfig:
        """获取调度配置"""
        return self._settings.scheduler
    
    @property
    def monitoring(self) -> MonitoringConfig:
        """获取监控配置"""
        return self._settings.monitoring
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """获取环境变量"""
        return os.getenv(key, default)
    
    def add_website(self, website: WebsiteConfig):
        """添加新网站"""
        self._websites.append(website)
        self._save_websites()
    
    def remove_website(self, url: str):
        """移除网站"""
        self._websites = [site for site in self._websites if site.url != url]
        self._save_websites()
    
    def update_website(self, url: str, **kwargs):
        """更新网站配置"""
        for site in self._websites:
            if site.url == url:
                for key, value in kwargs.items():
                    if hasattr(site, key):
                        setattr(site, key, value)
                break
        self._save_websites()
    
    def _save_websites(self):
        """保存网站配置到文件"""
        try:
            data = {
                "websites": [site.model_dump() for site in self._websites]
            }
            with open(self.websites_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存网站配置失败: {e}")
    
    def save_settings(self):
        """保存设置配置到文件"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._settings.model_dump(), f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"保存设置配置失败: {e}")


# 全局配置管理器实例
config = ConfigManager()
