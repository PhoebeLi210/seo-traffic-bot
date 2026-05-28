"""
排名查询服务 - 处理搜索引擎排名查询
"""

import re
import ssl
import urllib.request
from urllib.parse import quote
from typing import Dict
from loguru import logger


class RankService:
    """排名查询服务类"""

    # 搜索引擎URL模板
    ENGINE_URLS = {
        'google': 'https://www.google.com/search?q={keyword}&num=50&hl=en',
        'baidu': 'https://www.baidu.com/s?wd={keyword}&rn=50',
        'bing': 'https://www.bing.com/search?q={keyword}&count=50',
        '360': 'https://www.so.com/s?q={keyword}',
        'sogou': 'https://www.sogou.com/web?query={keyword}',
        'yisou': 'https://www.yisou.com/s?q={keyword}',
    }

    # PC端User-Agent
    PC_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # 移动端User-Agent
    MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'

    def check_rank(self, keyword: str, domain: str, engine: str, device: str = "pc") -> Dict:
        """
        查询指定关键词在搜索引擎中的排名

        Args:
            keyword: 搜索关键词
            domain: 网站域名
            engine: 搜索引擎 (google, baidu, bing, 360, sogou, yisou)
            device: 设备类型 ('pc' 或 'mobile')

        Returns:
            排名结果字典
        """
        url_template = self.ENGINE_URLS.get(engine)
        if not url_template:
            return {"engine": engine, "device": device, "rank": 0, "found": False}

        search_url = url_template.format(keyword=quote(keyword))

        # 根据设备类型选择User-Agent
        ua = self.MOBILE_UA if device == "mobile" else self.PC_UA

        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

        try:
            req = urllib.request.Request(search_url, headers=headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            # 提取所有链接
            links = re.findall(r'href=["\']?(https?://[^"\'\s>]+)', html)

            # 规范化domain用于匹配
            domain_lower = domain.lower().replace('https://', '').replace('http://', '').rstrip('/')
            if not domain_lower.startswith('www.'):
                domain_variants = [domain_lower, 'www.' + domain_lower]
            else:
                domain_variants = [domain_lower, domain_lower[4:]]

            position = 0
            for i, link in enumerate(links):
                link_lower = link.lower()
                for variant in domain_variants:
                    if variant in link_lower:
                        position = i + 1
                        break
                if position > 0:
                    break

            if position > 0:
                return {"engine": engine, "device": device, "rank": position, "found": True}
            else:
                return {"engine": engine, "device": device, "rank": 0, "found": False}

        except Exception as e:
            logger.error(f"排名查询失败 [{engine}/{device}]: {e}")
            return {"engine": engine, "device": device, "rank": 0, "found": False, "error": str(e)}

    def check_rank_multiple(self, keyword: str, domain: str, engines: list, device: str = "pc") -> list:
        """
        批量查询多个搜索引擎的排名

        Args:
            keyword: 搜索关键词
            domain: 网站域名
            engines: 搜索引擎列表
            device: 设备类型

        Returns:
            排名结果列表
        """
        results = []
        for engine in engines:
            result = self.check_rank(keyword, domain, engine, device)
            results.append(result)
        return results

    def get_supported_engines(self) -> list:
        """获取支持的搜索引擎列表"""
        return list(self.ENGINE_URLS.keys())


# 全局排名服务实例
rank_service = RankService()
