"""
排名查询服务 - 使用 Playwright 渲染搜索引擎页面获取真实排名
"""

import asyncio
import re
from urllib.parse import quote
from typing import Dict, List
from loguru import logger


class RankService:
    """排名查询服务类 - 使用 Playwright 渲染真实搜索结果"""

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

    async def check_rank_async(self, keyword: str, domain: str, engine: str, device: str = "pc") -> Dict:
        """
        使用 Playwright 异步查询排名
        """
        url_template = self.ENGINE_URLS.get(engine)
        if not url_template:
            return {"engine": engine, "device": device, "rank": 0, "found": False}

        search_url = url_template.format(keyword=quote(keyword))
        is_mobile = device == "mobile"

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                )

                # 创建上下文，添加额外的浏览器参数模拟真实用户
                context_options = {
                    'ignore_https_errors': True,
                    'extra_http_headers': {
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    }
                }

                if is_mobile:
                    context_options['user_agent'] = self.MOBILE_UA
                    context_options['viewport'] = {'width': 390, 'height': 844}
                    context_options['device_scale_factor'] = 3
                    context_options['is_mobile'] = True
                    context_options['has_touch'] = True
                else:
                    context_options['user_agent'] = self.PC_UA
                    context_options['viewport'] = {'width': 1920, 'height': 1080}

                context = await browser.new_context(**context_options)

                # 添加 cookies 以绕过某些检测
                if engine == 'baidu':
                    await context.add_cookies([
                        {'name': 'BAIDUID', 'value': 'XXXXXX', 'domain': '.baidu.com', 'path': '/'},
                        {'name': 'BDUSS', 'value': 'XXXXXX', 'domain': '.baidu.com', 'path': '/'},
                    ])

                page = await context.new_page()

                try:
                    # 访问搜索页面
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                    # 针对不同搜索引擎等待搜索结果加载
                    await self._wait_for_search_results(page, engine)

                    # 提取搜索结果链接
                    links = await self._extract_search_links(page, engine)

                    # 查找目标域名排名
                    position = self._find_domain_position(links, domain)

                    if position > 0:
                        logger.info(f"🔍 [{engine}/{device}] '{keyword}' → {domain} 排名第 {position} 位")
                        return {"engine": engine, "device": device, "rank": position, "found": True}
                    else:
                        logger.info(f"🔍 [{engine}/{device}] '{keyword}' → {domain} 未找到 (前{len(links)}名)")
                        return {"engine": engine, "device": device, "rank": 0, "found": False, "total_results": len(links)}

                except Exception as e:
                    logger.error(f"排名查询页面处理失败 [{engine}/{device}]: {e}")
                    return {"engine": engine, "device": device, "rank": 0, "found": False, "error": str(e)}

                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"排名查询失败 [{engine}/{device}]: {e}")
            return {"engine": engine, "device": device, "rank": 0, "found": False, "error": str(e)}

    async def _wait_for_search_results(self, page, engine: str):
        """等待搜索结果加载完成"""
        if engine == 'baidu':
            # 百度：等待结果容器加载，可能需要滚动页面触发加载
            try:
                await page.wait_for_selector('#content_left', timeout=15000)
            except:
                # 如果主容器没加载，等待备用选择器
                await page.wait_for_selector('.result', timeout=5000)
            # 滚动页面触发懒加载
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await asyncio.sleep(1)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

        elif engine == 'google':
            await page.wait_for_selector('#search', timeout=15000)
            # 滚动加载
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await asyncio.sleep(0.5)

        elif engine == 'bing':
            await page.wait_for_selector('#b_results', timeout=15000)

        elif engine == '360':
            await page.wait_for_selector('.result', timeout=15000)

        elif engine == 'sogou':
            await page.wait_for_selector('.results', timeout=15000)
            await asyncio.sleep(2)

        else:
            await asyncio.sleep(3)

    async def _extract_search_links(self, page, engine: str) -> List[str]:
        """从搜索结果页面提取链接"""
        links = []

        try:
            if engine == 'baidu':
                # 百度：提取 #content_left 中的所有链接
                # 先尝试提取真实链接（百度使用跳转）
                result_links = await page.eval_on_selector_all(
                    '#content_left h3 a[href], #content_left .c-title a[href], #content_left a[href^="http"]',
                    '''els => els.map(el => {
                        let href = el.href || '';
                        // 百度链接通常是 //www.baidu.com/links?cc=xxx 格式
                        // 或者有 data-url 属性
                        return el.getAttribute('data-url') || href;
                    }).filter(h => h && h.startsWith('http'))'''
                )
                links.extend(result_links)

                # 也尝试提取原始 href
                raw_links = await page.eval_on_selector_all(
                    '#content_left a[href^="http"]',
                    'els => els.map(e => e.href).filter(h => h && (h.startsWith("http") || h.startsWith("//")))'
                )
                for link in raw_links:
                    if link not in links:
                        links.append(link.lstrip('//') if link.startswith('//') else link)

            elif engine == 'google':
                links = await page.eval_on_selector_all(
                    '#search a[href^="http"]',
                    '''els => els.map(el => {
                        let href = el.href || '';
                        // 跳过 Google 内部链接
                        if (href.includes('google.com') && !href.includes('webcache')) return null;
                        return href;
                    }).filter(h => h)'''
                )

            else:
                # 通用方式
                all_links = await page.eval_on_selector_all(
                    'a[href^="http"]',
                    '''els => els.map(e => {
                        let href = e.href || '';
                        // 过滤掉明显不是搜索结果的链接
                        if (href.includes('baidu.com') && !href.includes('/s?')) return null;
                        if (href.includes('google.com/search')) return null;
                        if (href.includes('bing.com/search')) return null;
                        return href;
                    }).filter(h => h)'''
                )
                links.extend(all_links)

        except Exception as e:
            logger.error(f"提取搜索链接失败: {e}")

        # 去重
        seen = set()
        unique_links = []
        for link in links:
            if link and link not in seen:
                seen.add(link)
                unique_links.append(link)

        return unique_links

    def _find_domain_position(self, links: List[str], domain: str) -> int:
        """在链接列表中查找域名的排名位置"""
        domain_lower = domain.lower().replace('https://', '').replace('http://', '').rstrip('/')
        # 移除 www. 前缀以提高匹配率
        if domain_lower.startswith('www.'):
            domain_variants = [domain_lower, domain_lower[4:]]
        else:
            domain_variants = [domain_lower, 'www.' + domain_lower]

        for i, link in enumerate(links):
            link_lower = link.lower()
            for variant in domain_variants:
                if variant in link_lower:
                    return i + 1  # 排名从1开始

        return 0  # 未找到

    def check_rank(self, keyword: str, domain: str, engine: str, device: str = "pc") -> Dict:
        """
        同步接口：查询排名
        """
        try:
            return asyncio.run(self.check_rank_async(keyword, domain, engine, device))
        except RuntimeError as e:
            # 如果已经有事件循环在运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.check_rank_async(keyword, domain, engine, device))
                return future.result(timeout=45)

    def check_rank_multiple(self, keyword: str, domain: str, engines: list, device: str = "pc") -> list:
        """批量查询多个搜索引擎的排名"""
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
