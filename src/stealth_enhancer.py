"""
反检测增强模块 - 提供高级浏览器指纹伪装
"""

import random
from typing import Dict, Any, Optional
from playwright.async_api import Browser, BrowserContext, Page
from loguru import logger

from .config_manager import config


class StealthEnhancer:
    """反检测增强器"""
    
    # 常见的屏幕分辨率
    VIEWPORT_SIZES = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1280, "height": 720},
        {"width": 1600, "height": 900},
        {"width": 1680, "height": 1050},
        {"width": 2560, "height": 1440},
    ]
    
    # 常见的User-Agent
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0 Edg/120.0.0.0",
    ]
    
    # 常见的语言设置
    LOCALES = [
        "en-US",
        "en-GB",
        "zh-CN",
        "zh-TW",
        "ja-JP",
        "ko-KR",
        "de-DE",
        "fr-FR",
        "es-ES",
        "ru-RU",
    ]
    
    # 常见的时区
    TIMEZONES = [
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Shanghai",
        "Asia/Tokyo",
        "Asia/Seoul",
        "Australia/Sydney",
    ]
    
    def __init__(self):
        self.browser_config = config.browser
    
    def get_random_viewport(self) -> Dict[str, int]:
        """获取随机视口大小"""
        if self.browser_config.viewport:
            min_w = self.browser_config.viewport.get('min_width', 1200)
            max_w = self.browser_config.viewport.get('max_width', 1920)
            min_h = self.browser_config.viewport.get('min_height', 700)
            max_h = self.browser_config.viewport.get('max_height', 1080)
            return {
                "width": random.randint(min_w, max_w),
                "height": random.randint(min_h, max_h)
            }
        return random.choice(self.VIEWPORT_SIZES)
    
    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        if self.browser_config.user_agents:
            return random.choice(self.browser_config.user_agents)
        return random.choice(self.USER_AGENTS)
    
    def get_random_locale(self) -> str:
        """获取随机语言设置"""
        return random.choice(self.LOCALES)
    
    def get_random_timezone(self) -> str:
        """获取随机时区"""
        return random.choice(self.TIMEZONES)
    
    def get_context_options(self, proxy: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取浏览器上下文选项
        
        Args:
            proxy: 代理配置
            
        Returns:
            上下文选项字典
        """
        viewport = self.get_random_viewport()
        user_agent = self.get_random_user_agent()
        locale = self.get_random_locale()
        timezone = self.get_random_timezone()
        
        options = {
            "viewport": viewport,
            "user_agent": user_agent,
            "locale": locale,
            "timezone_id": timezone,
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
            "is_mobile": False,
            "has_touch": False,
            "permissions": ["geolocation"],
            "color_scheme": random.choice(["light", "dark"]),
            "accept_downloads": True,
        }
        
        if proxy:
            options["proxy"] = proxy
        
        logger.debug(f"创建浏览器上下文: viewport={viewport}, ua={user_agent[:50]}...")
        return options
    
    async def create_stealth_context(self, browser: Browser, proxy: Optional[Dict[str, str]] = None) -> BrowserContext:
        """
        创建反检测浏览器上下文
        
        Args:
            browser: 浏览器实例
            proxy: 代理配置
            
        Returns:
            浏览器上下文
        """
        context_options = self.get_context_options(proxy)
        context = await browser.new_context(**context_options)
        
        # 注入反检测脚本
        await self._inject_stealth_scripts(context)
        
        return context
    
    async def _inject_stealth_scripts(self, context: BrowserContext):
        """
        注入反检测脚本
        
        Args:
            context: 浏览器上下文
        """
        # 覆盖 navigator.webdriver 属性
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # 覆盖 plugins 和 mimeTypes
        await context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: ""},
                        description: "",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ]
            });
            
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => [
                    {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: navigator.plugins[1]},
                    {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: navigator.plugins[0]}
                ]
            });
        """)
        
        # 覆盖 chrome 对象
        await context.add_init_script("""
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
        """)
        
        # 覆盖 permissions API
        await context.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # 覆盖 webgl 参数
        await context.add_init_script("""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
        """)
        
        logger.debug("反检测脚本注入完成")


# 全局反检测增强器实例
stealth_enhancer = StealthEnhancer()
