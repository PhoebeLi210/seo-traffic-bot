"""
多用户Web仪表盘 - 支持用户登录、网站管理、关键词设置和数据统计
"""

import json
import os
import re
import secrets
import ssl
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote, quote
import threading
from loguru import logger

from .user_manager import user_manager, User
from .gsc_keyword_recommender import gsc_recommender
from .baidu_index_recommender import baidu_recommender, KeywordRecommendation


class MultiUserDashboard:
    """多用户仪表盘"""

    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.server_thread = None
        self.sessions: Dict[str, str] = {}  # session_id -> user_id

    def _get_user_websites_file(self, user_id: str) -> Path:
        """获取用户网站配置文件路径"""
        return user_manager.get_user_data_dir(user_id) / "config" / "websites.json"

    def _load_user_websites(self, user_id: str) -> List[Dict]:
        """加载用户的网站列表"""
        f = self._get_user_websites_file(user_id)
        if f.exists():
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    return json.load(fp).get('websites', [])
            except Exception:
                return []
        return []

    def _save_user_websites(self, user_id: str, websites: List[Dict]):
        """保存用户的网站列表"""
        f = self._get_user_websites_file(user_id)
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, 'w', encoding='utf-8') as fp:
            json.dump({'websites': websites}, fp, ensure_ascii=False, indent=2)

    def _get_user_stats_dir(self, user_id: str) -> Path:
        """获取用户统计目录"""
        return user_manager.get_user_data_dir(user_id) / "stats"

    def _get_user_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """获取用户统计数据"""
        stats_dir = self._get_user_stats_dir(user_id)
        total_visits = 0
        success_visits = 0
        failed_visits = 0
        website_summary = {}
        daily_data = []

        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            stats_file = stats_dir / f"{target_date.isoformat()}.json"
            if stats_file.exists():
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        daily_data.append(data)
                        total_visits += data.get("total_visits", 0)
                        success_visits += data.get("successful_visits", 0)
                        failed_visits += data.get("failed_visits", 0)
                        for url, site_data in data.get("websites", {}).items():
                            if url not in website_summary:
                                website_summary[url] = {"visits": 0, "success": 0, "failed": 0}
                            website_summary[url]["visits"] += site_data.get("total_visits", 0)
                            website_summary[url]["success"] += site_data.get("successful_visits", 0)
                            website_summary[url]["failed"] += site_data.get("failed_visits", 0)
                except Exception:
                    pass

        return {
            "total_visits": total_visits,
            "success_visits": success_visits,
            "failed_visits": failed_visits,
            "success_rate": (success_visits / total_visits * 100) if total_visits > 0 else 0,
            "website_summary": website_summary,
            "daily_data": daily_data,
            "days": days
        }

    def _check_rank(self, keyword: str, domain: str, engine: str, device: str = "pc") -> dict:
        """查询指定关键词在搜索引擎中的排名
        device: 'pc' 或 'mobile'
        """
        engine_urls = {
            'google': 'https://www.google.com/search?q={keyword}&num=50&hl=en',
            'baidu': 'https://www.baidu.com/s?wd={keyword}&rn=50',
            'bing': 'https://www.bing.com/search?q={keyword}&count=50',
            '360': 'https://www.so.com/s?q={keyword}',
            'sogou': 'https://www.sogou.com/web?query={keyword}',
            'yisou': 'https://www.yisou.com/s?q={keyword}',
        }

        url_template = engine_urls.get(engine)
        if not url_template:
            return {"engine": engine, "device": device, "rank": 0, "found": False}

        search_url = url_template.format(keyword=quote(keyword))

        # 根据设备类型使用不同的 User-Agent
        if device == "mobile":
            ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        else:
            ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

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

            # 规范化 domain 用于匹配
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

    # ==================== 页面生成 ====================

    def generate_login_page(self, error: str = None) -> str:
        error_html = f'<div class="error">{error}</div>' if error else ''
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - SEO Traffic Bot</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .box {{ background: white; padding: 40px; border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 400px; }}
        h1 {{ text-align: center; color: #333; margin-bottom: 30px; font-size: 1.8em; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 8px; color: #555; font-weight: 500; }}
        input {{ width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0;
            border-radius: 10px; font-size: 1em; transition: border-color 0.3s; }}
        input:focus {{ outline: none; border-color: #667eea; }}
        button {{ width: 100%; padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 10px; font-size: 1em;
            font-weight: 600; cursor: pointer; transition: transform 0.3s, box-shadow 0.3s; }}
        button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102,126,234,0.4); }}
        .error {{ background: #fee; color: #c33; padding: 12px; border-radius: 8px;
            margin-bottom: 20px; text-align: center; }}
        .links {{ text-align: center; margin-top: 20px; }}
        .links a {{ color: #667eea; text-decoration: none; }}
        .links a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>🔐 用户登录</h1>
        {error_html}
        <form method="POST" action="/login">
            <div class="form-group">
                <label>用户名或邮箱</label>
                <input type="text" name="username" required placeholder="请输入用户名">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" required placeholder="请输入密码">
            </div>
            <button type="submit">登录</button>
        </form>
        <div class="links">
            <a href="/register">还没有账号？立即注册</a>
        </div>
    </div>
</body>
</html>"""

    def generate_register_page(self, error: str = None) -> str:
        error_html = f'<div class="error">{error}</div>' if error else ''
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 - SEO Traffic Bot</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .box {{ background: white; padding: 40px; border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 400px; }}
        h1 {{ text-align: center; color: #333; margin-bottom: 30px; font-size: 1.8em; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 8px; color: #555; font-weight: 500; }}
        input {{ width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0;
            border-radius: 10px; font-size: 1em; transition: border-color 0.3s; }}
        input:focus {{ outline: none; border-color: #667eea; }}
        button {{ width: 100%; padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 10px; font-size: 1em;
            font-weight: 600; cursor: pointer; transition: transform 0.3s, box-shadow 0.3s; }}
        button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102,126,234,0.4); }}
        .error {{ background: #fee; color: #c33; padding: 12px; border-radius: 8px;
            margin-bottom: 20px; text-align: center; }}
        .links {{ text-align: center; margin-top: 20px; }}
        .links a {{ color: #667eea; text-decoration: none; }}
        .links a:hover {{ text-decoration: underline; }}
        .plan-info {{ background: #f0f4ff; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
        .plan-info h3 {{ color: #667eea; margin-bottom: 10px; }}
        .plan-info ul {{ list-style: none; color: #555; }}
        .plan-info li {{ padding: 5px 0; padding-left: 20px; position: relative; }}
        .plan-info li:before {{ content: "✓"; position: absolute; left: 0; color: #10b981; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="box">
        <h1>📝 用户注册</h1>
        <div class="plan-info">
            <h3>免费版包含：</h3>
            <ul>
                <li>最多8个网站</li>
                <li>每日20次访问/网站</li>
                <li>基础统计数据</li>
                <li>邮件技术支持</li>
            </ul>
        </div>
        {error_html}
        <form method="POST" action="/register">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" required placeholder="设置用户名">
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" name="email" required placeholder="输入邮箱地址">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" required placeholder="设置密码（至少6位）">
            </div>
            <div class="form-group">
                <label>确认密码</label>
                <input type="password" name="password_confirm" required placeholder="再次输入密码">
            </div>
            <button type="submit">注册</button>
        </form>
        <div class="links">
            <a href="/login">已有账号？立即登录</a>
        </div>
    </div>
</body>
</html>"""

    def generate_dashboard_page(self, user_id: str, active_tab: str = "websites") -> str:
        """生成主仪表盘页面 - 包含网站管理、关键词设置、统计查看"""
        user = user_manager.get_user_by_id(user_id)
        if not user:
            return self.generate_login_page("请先登录")

        websites = self._load_user_websites(user_id)
        stats = self._get_user_stats(user_id, days=7)

        # 生成网站列表行
        website_rows = ""
        for i, ws in enumerate(websites):
            url = ws.get("url", "")
            keywords = ws.get("keywords", [])
            daily_visits = ws.get("daily_visits", 10)
            enabled = ws.get("enabled", True)
            status_badge = '<span class="badge badge-success">运行中</span>' if enabled else '<span class="badge badge-gray">已暂停</span>'
            kw_text = ", ".join(keywords[:3]) + (f" (+{len(keywords)-3})" if len(keywords) > 3 else "") if keywords else '<span class="text-muted">未设置</span>'
            website_rows += f"""
            <tr data-index="{i}">
                <td><a href="{url}" target="_blank" class="url-link">{url[:45]}{'...' if len(url)>45 else ''}</a></td>
                <td>{kw_text}</td>
                <td class="center">{daily_visits}</td>
                <td class="center">{status_badge}</td>
                <td class="center">
                    <button class="btn btn-sm btn-primary" onclick="editSite({i})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSite({i})">删除</button>
                </td>
            </tr>"""

        if not website_rows:
            website_rows = """<tr><td colspan="5" class="empty-state">
                <div class="empty-icon">🌐</div>
                <p>还没有添加网站</p>
                <p class="text-muted">点击上方"添加网站"按钮开始</p>
            </td></tr>"""

        # 生成统计行
        stats_rows = ""
        for url, data in sorted(stats["website_summary"].items(), key=lambda x: x[1]["visits"], reverse=True):
            rate = (data["success"] / data["visits"] * 100) if data["visits"] > 0 else 0
            stats_rows += f"""
            <tr>
                <td class="url-cell">{url[:50]}{'...' if len(url)>50 else ''}</td>
                <td class="center">{data['visits']}</td>
                <td class="center text-success">{data['success']}</td>
                <td class="center text-danger">{data['failed']}</td>
                <td class="center">{rate:.1f}%</td>
            </tr>"""
        if not stats_rows:
            stats_rows = """<tr><td colspan="5" class="empty-state">
                <div class="empty-icon">📊</div>
                <p>暂无统计数据</p>
                <p class="text-muted">添加网站并运行后，这里会显示访问数据</p>
            </td></tr>"""

        # 准备网站数据给JS
        websites_json = json.dumps(websites, ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Traffic Bot - 控制面板</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5; min-height: 100vh; }}

        /* 顶部导航 */
        .navbar {{ background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 0 30px; display: flex; align-items: center; height: 60px;
            position: sticky; top: 0; z-index: 100; }}
        .navbar .logo {{ font-size: 1.3em; font-weight: 700; color: #667eea; margin-right: 40px; }}
        .navbar .nav-tabs {{ display: flex; gap: 5px; }}
        .navbar .nav-tab {{ padding: 10px 20px; border-radius: 8px; cursor: pointer;
            color: #666; font-weight: 500; transition: all 0.2s; border: none; background: none; font-size: 0.95em; }}
        .navbar .nav-tab:hover {{ background: #f0f2f5; color: #333; }}
        .navbar .nav-tab.active {{ background: #667eea; color: white; }}
        .navbar .user-info {{ margin-left: auto; display: flex; align-items: center; gap: 12px; }}
        .navbar .user-name {{ font-weight: 600; color: #333; }}
        .navbar .plan-badge {{ background: #667eea; color: white; padding: 3px 10px;
            border-radius: 12px; font-size: 0.75em; }}
        .navbar .logout-btn {{ color: #ef4444; text-decoration: none; font-size: 0.9em; cursor: pointer;
            background: none; border: none; }}
        .navbar .logout-btn:hover {{ text-decoration: underline; }}

        /* 主内容 */
        .main {{ max-width: 1100px; margin: 0 auto; padding: 25px 20px; }}

        /* 统计卡片 */
        .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 25px; }}
        .stat-card {{ background: white; border-radius: 12px; padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .stat-card .label {{ font-size: 0.85em; color: #888; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 1.8em; font-weight: 700; color: #333; }}
        .stat-card .value.green {{ color: #10b981; }}
        .stat-card .value.red {{ color: #ef4444; }}
        .stat-card .value.blue {{ color: #667eea; }}

        /* 操作栏 */
        .action-bar {{ display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; }}
        .action-bar h2 {{ font-size: 1.2em; color: #333; }}
        .action-bar .hint {{ font-size: 0.85em; color: #888; }}

        /* 按钮 */
        .btn {{ padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
            font-size: 0.9em; font-weight: 500; transition: all 0.2s; }}
        .btn-primary {{ background: #667eea; color: white; }}
        .btn-primary:hover {{ background: #5a67d8; }}
        .btn-success {{ background: #10b981; color: white; }}
        .btn-success:hover {{ background: #059669; }}
        .btn-danger {{ background: #ef4444; color: white; }}
        .btn-danger:hover {{ background: #dc2626; }}
        .btn-sm {{ padding: 5px 12px; font-size: 0.8em; }}
        .btn-gray {{ background: #e5e7eb; color: #555; }}
        .btn-gray:hover {{ background: #d1d5db; }}

        /* 表格 */
        .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            overflow: hidden; }}
        .card table {{ width: 100%; border-collapse: collapse; }}
        .card th {{ background: #f8fafc; padding: 12px 16px; text-align: left;
            font-weight: 600; color: #475569; font-size: 0.85em; text-transform: uppercase;
            letter-spacing: 0.5px; border-bottom: 1px solid #e2e8f0; }}
        .card td {{ padding: 12px 16px; border-bottom: 1px solid #f1f5f9; font-size: 0.9em; color: #333; }}
        .card tr:hover {{ background: #f8fafc; }}
        .center {{ text-align: center; }}
        .url-link {{ color: #667eea; text-decoration: none; }}
        .url-link:hover {{ text-decoration: underline; }}
        .url-cell {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .text-muted {{ color: #aaa; }}
        .text-success {{ color: #10b981; }}
        .text-danger {{ color: #ef4444; }}

        /* 徽章 */
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }}
        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-gray {{ background: #f1f5f9; color: #64748b; }}

        /* 空状态 */
        .empty-state {{ text-align: center; padding: 40px 20px !important; }}
        .empty-icon {{ font-size: 2.5em; margin-bottom: 10px; }}
        .empty-state p {{ color: #666; margin-bottom: 5px; }}

        /* 模态框 */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 200; align-items: center; justify-content: center; }}
        .modal-overlay.show {{ display: flex; }}
        .modal {{ background: white; border-radius: 16px; padding: 30px; width: 90%; max-width: 520px;
            max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        .modal h2 {{ margin-bottom: 20px; color: #333; font-size: 1.3em; }}
        .modal .form-group {{ margin-bottom: 16px; }}
        .modal label {{ display: block; margin-bottom: 6px; color: #555; font-weight: 500; font-size: 0.9em; }}
        .modal input[type="text"], .modal input[type="url"], .modal input[type="number"] {{
            width: 100%; padding: 10px 14px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 0.95em; }}
        .modal input:focus {{ outline: none; border-color: #667eea; }}
        .modal .hint {{ font-size: 0.8em; color: #999; margin-top: 4px; }}
        .modal .btn-row {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }}
        .modal .keywords-area {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
        .modal .keyword-tag {{ background: #eef2ff; color: #667eea; padding: 4px 10px;
            border-radius: 6px; font-size: 0.85em; display: flex; align-items: center; gap: 6px; }}
        .modal .keyword-tag .remove {{ cursor: pointer; color: #aaa; font-weight: bold; }}
        .modal .keyword-tag .remove:hover {{ color: #ef4444; }}
        .modal .kw-input-row {{ display: flex; gap: 8px; margin-top: 8px; }}
        .modal .kw-input-row input {{ flex: 1; }}
        .modal .kw-input-row button {{ white-space: nowrap; }}
        .modal .toggle-row {{ display: flex; align-items: center; gap: 10px; }}
        .modal .toggle {{ width: 44px; height: 24px; border-radius: 12px; background: #ddd;
            position: relative; cursor: pointer; transition: background 0.3s; }}
        .modal .toggle.on {{ background: #667eea; }}
        .modal .toggle::after {{ content: ''; position: absolute; top: 2px; left: 2px;
            width: 20px; height: 20px; border-radius: 50%; background: white;
            transition: transform 0.3s; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}
        .modal .toggle.on::after {{ transform: translateX(20px); }}

        /* Tab内容切换 */
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        /* 排名查询 */
        .rank-query-card {{ padding: 20px; }}
        .rank-form {{ display: flex; flex-direction: column; gap: 16px; }}
        .rank-form-row {{ display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; }}
        .rank-form-group {{ flex: 1; min-width: 200px; }}
        .rank-form-group label {{ display: block; margin-bottom: 6px; color: #555; font-weight: 500; font-size: 0.9em; }}
        .rank-form-group select,
        .rank-form-group input[type="text"] {{ width: 100%; padding: 10px 14px; border: 2px solid #e0e0e0;
            border-radius: 8px; font-size: 0.95em; }}
        .rank-form-group select:focus,
        .rank-form-group input[type="text"]:focus {{ outline: none; border-color: #667eea; }}
        .rank-engines-group {{ flex: unset; width: 100%; }}
        .rank-checkboxes {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 4px; }}
        .rank-checkbox {{ display: flex; align-items: center; gap: 6px; cursor: pointer;
            font-size: 0.9em; color: #444; padding: 6px 12px; border: 1px solid #e0e0e0;
            border-radius: 6px; transition: all 0.2s; }}
        .rank-checkbox:hover {{ border-color: #667eea; background: #f8f9ff; }}
        .rank-checkbox input[type="checkbox"] {{ width: 16px; height: 16px; cursor: pointer; }}
        .rank-loading {{ color: #667eea; font-style: italic; }}
        .rank-found {{ color: #10b981; font-weight: 700; }}
        .rank-not-found {{ color: #ef4444; }}

        /* 响应式 - 移动端优化 */
        @media (max-width: 768px) {{
            /* 导航栏改为两行布局 */
            .navbar {{
                flex-wrap: wrap;
                height: auto;
                padding: 12px 15px;
            }}
            .navbar .logo {{
                font-size: 1.1em;
                margin-right: 0;
                width: 100%;
                text-align: center;
                margin-bottom: 10px;
            }}
            .navbar .nav-tabs {{
                width: 100%;
                justify-content: center;
                gap: 8px;
            }}
            .navbar .nav-tab {{
                padding: 8px 16px;
                font-size: 0.9em;
            }}
            .navbar .user-info {{
                width: 100%;
                justify-content: center;
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px solid #eee;
            }}
            
            /* 统计卡片 2列布局，紧凑样式 */
            .stats-row {{
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-bottom: 20px;
            }}
            .stat-card {{
                padding: 15px;
            }}
            .stat-card .label {{
                font-size: 0.75em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .stat-card .value {{
                font-size: 1.5em;
            }}
            
            /* 操作栏 */
            .action-bar {{
                flex-direction: column;
                gap: 12px;
                align-items: stretch;
            }}
            .action-bar h2 {{
                font-size: 1.1em;
            }}
            .action-bar .btn {{
                width: 100%;
            }}
            
            /* 表格改为卡片式 */
            .card {{
                border-radius: 8px;
            }}
            .card th {{
                padding: 10px 12px;
                font-size: 0.8em;
            }}
            .card td {{
                padding: 10px 12px;
                font-size: 0.85em;
            }}
            /* 移动端隐藏部分表格列 */
            .card th:nth-child(2),
            .card td:nth-child(2),
            .card th:nth-child(3),
            .card td:nth-child(3) {{
                display: none;
            }}
            .url-link {{
                font-size: 0.85em;
            }}
            
            /* 模态框 */
            .modal {{
                padding: 20px;
                width: 95%;
                max-height: 85vh;
            }}
            .modal h2 {{
                font-size: 1.1em;
            }}

            /* 排名查询移动端适配 */
            .rank-query-card {{
                padding: 15px;
            }}
            .rank-form-row {{
                flex-direction: column;
                gap: 12px;
            }}
            .rank-form-group {{
                min-width: unset;
                width: 100%;
            }}
            .rank-checkboxes {{
                gap: 8px;
            }}
            .rank-checkbox {{
                font-size: 0.8em;
                padding: 5px 8px;
            }}
        }}
        
        /* 超小屏幕 (< 480px) */
        @media (max-width: 480px) {{
            .navbar .nav-tab {{
                padding: 6px 10px;
                font-size: 0.8em;
            }}
            .navbar .user-name {{
                font-size: 0.85em;
            }}
            .stats-row {{
                grid-template-columns: 1fr 1fr;
                gap: 8px;
            }}
            .stat-card {{
                padding: 12px;
            }}
            .stat-card .value {{
                font-size: 1.3em;
            }}
            .main {{
                padding: 15px 10px;
            }}
            .rank-checkbox {{
                font-size: 0.75em;
                padding: 4px 6px;
            }}
            .rank-checkboxes {{
                gap: 6px;
            }}
        }}
    </style>
</head>
<body>

<!-- 导航栏 -->
<nav class="navbar">
    <div class="logo">🚀 SEO Traffic Bot</div>
    <div class="nav-tabs">
        <button class="nav-tab active" onclick="switchTab('websites')">🌐 网站管理</button>
        <button class="nav-tab" onclick="switchTab('stats')">📊 统计数据</button>
        <button class="nav-tab" onclick="switchTab('rank')">🔍 排名查询</button>
    </div>
    <div class="user-info">
        <span class="user-name">👤 {user.username}</span>
        <span class="plan-badge">{user.plan.upper()}</span>
        <button class="logout-btn" onclick="location.href='/logout'">退出</button>
    </div>
</nav>

<!-- 主内容 -->
<div class="main">

    <!-- 概览统计 -->
    <div class="stats-row">
        <div class="stat-card">
            <div class="label">网站数量</div>
            <div class="value blue">{len(websites)}</div>
        </div>
        <div class="stat-card">
            <div class="label">总访问次数 (7天)</div>
            <div class="value">{stats['total_visits']}</div>
        </div>
        <div class="stat-card">
            <div class="label">成功访问</div>
            <div class="value green">{stats['success_visits']}</div>
        </div>
        <div class="stat-card">
            <div class="label">成功率</div>
            <div class="value">{stats['success_rate']:.1f}%</div>
        </div>
    </div>

    <!-- 网站管理 Tab -->
    <div id="tab-websites" class="tab-content active">
        <div class="action-bar">
            <div>
                <h2>网站管理</h2>
                <span class="hint">已使用 {len(websites)}/{user.max_websites} 个网站名额</span>
            </div>
            <button class="btn btn-primary" onclick="openAddModal()">＋ 添加网站</button>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>网站地址</th>
                        <th>搜索关键词</th>
                        <th class="center">每日访问</th>
                        <th class="center">状态</th>
                        <th class="center">操作</th>
                    </tr>
                </thead>
                <tbody id="website-tbody">
                    {website_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- 统计数据 Tab -->
    <div id="tab-stats" class="tab-content">
        <div class="action-bar">
            <div>
                <h2>访问统计 (最近7天)</h2>
                <span class="hint">数据每日自动更新</span>
            </div>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>网站</th>
                        <th class="center">总访问</th>
                        <th class="center">成功</th>
                        <th class="center">失败</th>
                        <th class="center">成功率</th>
                    </tr>
                </thead>
                <tbody>
                    {stats_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- 排名查询 Tab -->
    <div id="tab-rank" class="tab-content">
        <div class="action-bar">
            <div>
                <h2>搜索引擎排名查询</h2>
                <span class="hint">分别查询PC端和移动端的排名，结果可能不同</span>
            </div>
        </div>
        <div class="card rank-query-card">
            <div class="rank-form">
                <div class="rank-form-row">
                    <div class="rank-form-group">
                        <label>选择网站</label>
                        <select id="rankDomain">
                            <option value="">-- 请选择网站 --</option>
                        </select>
                    </div>
                    <div class="rank-form-group">
                        <label>输入关键词</label>
                        <input type="text" id="rankKeyword" placeholder="请输入要查询的关键词">
                    </div>
                </div>
                <div class="rank-form-row">
                    <div class="rank-form-group rank-engines-group">
                        <label>选择搜索引擎</label>
                        <div class="rank-checkboxes">
                            <label class="rank-checkbox"><input type="checkbox" value="google" checked> Google</label>
                            <label class="rank-checkbox"><input type="checkbox" value="baidu" checked> 百度</label>
                            <label class="rank-checkbox"><input type="checkbox" value="bing" checked> Bing</label>
                            <label class="rank-checkbox"><input type="checkbox" value="360" checked> 360搜索</label>
                            <label class="rank-checkbox"><input type="checkbox" value="sogou" checked> 搜狗</label>
                            <label class="rank-checkbox"><input type="checkbox" value="yisou" checked> 一搜</label>
                        </div>
                    </div>
                </div>
                <div class="rank-form-row">
                    <div class="rank-form-group rank-engines-group">
                        <label>查询设备</label>
                        <div class="rank-checkboxes">
                            <label class="rank-checkbox"><input type="checkbox" value="pc" checked> 🖥️ PC端</label>
                            <label class="rank-checkbox"><input type="checkbox" value="mobile" checked> 📱 移动端</label>
                        </div>
                    </div>
                </div>
                <div class="rank-form-row">
                    <button class="btn btn-primary" id="rankQueryBtn" onclick="checkRank()">开始查询</button>
                </div>
            </div>
        </div>
        <div class="card rank-result-card" style="margin-top: 16px;">
            <table>
                <thead>
                    <tr>
                        <th>搜索引擎</th>
                        <th>设备</th>
                        <th class="center">排名</th>
                        <th class="center">状态</th>
                    </tr>
                </thead>
                <tbody id="rankResultBody">
                    <tr><td colspan="4" class="empty-state">
                        <div class="empty-icon">🔍</div>
                        <p>请选择网站并输入关键词后查询</p>
                    </td></tr>
                </tbody>
            </table>
        </div>
    </div>

</div>

<!-- 添加/编辑网站 模态框 -->
<div class="modal-overlay" id="siteModal">
    <div class="modal">
        <h2 id="modalTitle">添加网站</h2>
        <form id="siteForm" onsubmit="saveSite(event)">
            <input type="hidden" id="editIndex" value="-1">
            <div class="form-group">
                <label>网站地址</label>
                <input type="url" id="siteUrl" required placeholder="https://example.com">
                <div class="hint">输入完整的网站URL，包含 https://</div>
            </div>
            <div class="form-group">
                <label>搜索关键词</label>
                <div class="hint" style="margin-bottom:6px;">设置搜索引擎用来找到你网站的关键词，每行一个或用逗号分隔</div>
                <div class="keywords-area" id="keywordsArea"></div>
                <div class="kw-input-row">
                    <input type="text" id="kwInput" placeholder="输入关键词后按回车或点击添加">
                    <button type="button" class="btn btn-gray" onclick="addKeyword()">添加</button>
                </div>
                <div class="kw-recommend-row" style="margin-top: 10px;">
                    <button type="button" class="btn btn-success" id="recommendBtn" onclick="fetchRecommendedKeywords()">
                        🔍 获取GSC推荐关键词
                    </button>
                    <span class="hint" style="margin-left: 8px; font-size: 0.8em;">从Google Search Console获取排名4-20位的高潜力关键词</span>
                </div>
                <div class="kw-recommend-row" style="margin-top: 8px;">
                    <button type="button" class="btn btn-primary" id="baiduRecommendBtn" onclick="fetchBaiduRecommendations()">
                        📊 百度指数关键词推荐
                    </button>
                    <span class="hint" style="margin-left: 8px; font-size: 0.8em;">基于行业词库和搜索热度分析推荐关键词</span>
                </div>
                <div id="recommendStatus" style="margin-top: 8px; font-size: 0.85em; color: #667eea;"></div>
                <div id="baiduRecommendResult" style="margin-top: 12px; display: none;">
                    <div style="background: #f8fafc; border-radius: 8px; padding: 12px; max-height: 300px; overflow-y: auto;">
                        <table style="width: 100%; font-size: 0.85em;">
                            <thead>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <th style="text-align: left; padding: 6px;">关键词</th>
                                    <th style="text-align: center; padding: 6px;">类别</th>
                                    <th style="text-align: center; padding: 6px;">搜索量</th>
                                    <th style="text-align: center; padding: 6px;">竞争</th>
                                    <th style="text-align: center; padding: 6px;">趋势</th>
                                    <th style="text-align: center; padding: 6px;">操作</th>
                                </tr>
                            </thead>
                            <tbody id="baiduRecommendTable"></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>每日访问次数</label>
                <input type="number" id="dailyVisits" min="1" max="100" value="10">
                <div class="hint">免费版每个网站每天最多 {user.max_daily_visits} 次</div>
            </div>
            <div class="form-group">
                <div class="toggle-row">
                    <div class="toggle on" id="enabledToggle" onclick="toggleEnabled()"></div>
                    <label style="margin:0;">启用此网站</label>
                </div>
            </div>
            <div class="btn-row">
                <button type="button" class="btn btn-gray" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">保存</button>
            </div>
        </form>
    </div>
</div>

<script>
// 网站数据
let websites = {websites_json};
let currentKeywords = [];

// Tab切换
function switchTab(tab) {{
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    event.target.classList.add('active');
}}

// 打开添加模态框
function openAddModal() {{
    if (websites.length >= {user.max_websites}) {{
        alert('已达到最大网站数量限制 ({user.max_websites}个)');
        return;
    }}
    document.getElementById('modalTitle').textContent = '添加网站';
    document.getElementById('editIndex').value = -1;
    document.getElementById('siteUrl').value = '';
    document.getElementById('dailyVisits').value = 10;
    currentKeywords = [];
    renderKeywords();
    setToggle(true);
    document.getElementById('siteModal').classList.add('show');
}}

// 编辑网站
function editSite(index) {{
    const site = websites[index];
    document.getElementById('modalTitle').textContent = '编辑网站';
    document.getElementById('editIndex').value = index;
    document.getElementById('siteUrl').value = site.url || '';
    document.getElementById('dailyVisits').value = site.daily_visits || 10;
    currentKeywords = site.keywords ? [...site.keywords] : [];
    renderKeywords();
    setToggle(site.enabled !== false);
    document.getElementById('siteModal').classList.add('show');
}}

// 删除网站
function deleteSite(index) {{
    if (!confirm('确定要删除这个网站吗？')) return;
    websites.splice(index, 1);
    saveToServer();
}}

// 关闭模态框
function closeModal() {{
    document.getElementById('siteModal').classList.remove('show');
}}

// 关键词管理
function addKeyword() {{
    const input = document.getElementById('kwInput');
    const kw = input.value.trim();
    if (kw && !currentKeywords.includes(kw)) {{
        currentKeywords.push(kw);
        renderKeywords();
    }}
    input.value = '';
    input.focus();
}}

function removeKeyword(idx) {{
    currentKeywords.splice(idx, 1);
    renderKeywords();
}}

function renderKeywords() {{
    const area = document.getElementById('keywordsArea');
    area.innerHTML = currentKeywords.map((kw, i) =>
        `<span class="keyword-tag">${{kw}} <span class="remove" onclick="removeKeyword(${{i}})">×</span></span>`
    ).join('');
}}

// 回车添加关键词
document.addEventListener('DOMContentLoaded', function() {{
    document.getElementById('kwInput').addEventListener('keydown', function(e) {{
        if (e.key === 'Enter') {{ e.preventDefault(); addKeyword(); }}
    }});
}});

// Toggle开关
function toggleEnabled() {{
    const toggle = document.getElementById('enabledToggle');
    toggle.classList.toggle('on');
}}
function setToggle(on) {{
    const toggle = document.getElementById('enabledToggle');
    if (on) toggle.classList.add('on');
    else toggle.classList.remove('on');
}}

// 保存网站
function saveSite(e) {{
    e.preventDefault();
    const index = parseInt(document.getElementById('editIndex').value);
    const site = {{
        url: document.getElementById('siteUrl').value.trim(),
        keywords: [...currentKeywords],
        daily_visits: parseInt(document.getElementById('dailyVisits').value) || 10,
        enabled: document.getElementById('enabledToggle').classList.contains('on'),
        search_engine: 'google'
    }};

    if (index >= 0) {{
        websites[index] = site;
    }} else {{
        websites.push(site);
    }}

    saveToServer();
    closeModal();
}}

// 保存到服务器
function saveToServer() {{
    fetch('/api/websites', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{websites: websites}})
    }}).then(r => r.json()).then(data => {{
        if (data.success) {{
            location.reload();
        }} else {{
            alert('保存失败: ' + (data.error || '未知错误'));
        }}
    }}).catch(err => alert('网络错误: ' + err));
}}

// ==================== 排名查询 ====================

const engineNames = {{
    'google': 'Google',
    'baidu': '百度',
    'bing': 'Bing',
    '360': '360搜索',
    'sogou': '搜狗',
    'yisou': '一搜'
}};

const deviceNames = {{
    'pc': '🖥️ PC端',
    'mobile': '📱 移动端'
}};

// 初始化排名查询的网站下拉框
function initRankDropdown() {{
    const select = document.getElementById('rankDomain');
    select.innerHTML = '<option value="">-- 请选择网站 --</option>';
    websites.forEach(ws => {{
        const opt = document.createElement('option');
        opt.value = ws.url;
        opt.textContent = ws.url.length > 50 ? ws.url.substring(0, 50) + '...' : ws.url;
        select.appendChild(opt);
    }});
}}

// 排名查询
async function checkRank() {{
    const domain = document.getElementById('rankDomain').value;
    const keyword = document.getElementById('rankKeyword').value.trim();

    if (!domain) {{ alert('请选择一个网站'); return; }}
    if (!keyword) {{ alert('请输入关键词'); return; }}

    const engineBoxes = document.querySelectorAll('.rank-checkboxes input[type="checkbox"][value="google"],.rank-checkboxes input[type="checkbox"][value="baidu"],.rank-checkboxes input[type="checkbox"][value="bing"],.rank-checkboxes input[type="checkbox"][value="360"],.rank-checkboxes input[type="checkbox"][value="sogou"],.rank-checkboxes input[type="checkbox"][value="yisou"]:checked');
    const deviceBoxes = document.querySelectorAll('.rank-checkboxes input[type="checkbox"][value="pc"]:checked, .rank-checkboxes input[type="checkbox"][value="mobile"]:checked');

    // 用更精确的方式获取选中的引擎和设备
    const allCheckboxes = document.querySelectorAll('.rank-checkboxes input[type="checkbox"]:checked');
    const engines = [];
    const devices = [];
    allCheckboxes.forEach(cb => {{
        const v = cb.value;
        if (['google','baidu','bing','360','sogou','yisou'].includes(v)) engines.push(v);
        if (['pc','mobile'].includes(v)) devices.push(v);
    }});

    if (engines.length === 0) {{ alert('请至少选择一个搜索引擎'); return; }}
    if (devices.length === 0) {{ alert('请至少选择一种设备类型'); return; }}

    const tbody = document.getElementById('rankResultBody');
    const btn = document.getElementById('rankQueryBtn');

    btn.disabled = true;
    btn.textContent = '查询中...';

    // 生成所有查询任务 (引擎 x 设备)
    let rows = '';
    let taskId = 0;
    const tasks = [];
    engines.forEach(eng => {{
        devices.forEach(dev => {{
            const id = 'rank-row-' + taskId++;
            tasks.push({{id, eng, dev}});
            rows += `<tr id="${{id}}">
                <td>${{engineNames[eng] || eng}}</td>
                <td>${{deviceNames[dev] || dev}}</td>
                <td class="center rank-loading">查询中...</td>
                <td class="center rank-loading">查询中...</td>
            </tr>`;
        }});
    }});
    tbody.innerHTML = rows;

    // 逐个查询
    for (const task of tasks) {{
        const row = document.getElementById(task.id);
        try {{
            const resp = await fetch(`/api/rank?engine=${{encodeURIComponent(task.eng)}}&keyword=${{encodeURIComponent(keyword)}}&domain=${{encodeURIComponent(domain)}}&device=${{encodeURIComponent(task.dev)}}`);
            const data = await resp.json();
            if (data.found) {{
                row.cells[2].innerHTML = `<span class="rank-found">第 ${{data.rank}} 名</span>`;
                row.cells[3].innerHTML = '<span class="rank-found">已找到</span>';
            }} else {{
                row.cells[2].innerHTML = '-';
                row.cells[3].innerHTML = '<span class="rank-not-found">未找到 (前50名)</span>';
            }}
        }} catch (err) {{
            row.cells[2].innerHTML = '-';
            row.cells[3].innerHTML = '<span class="rank-not-found">查询失败</span>';
        }}
    }}

    btn.disabled = false;
    btn.textContent = '开始查询';
}}

// 页面加载时初始化排名下拉框
document.addEventListener('DOMContentLoaded', function() {{
    initRankDropdown();
}});

// ==================== 获取GSC推荐关键词 ====================

async function fetchRecommendedKeywords() {{
    const url = document.getElementById('siteUrl').value.trim();
    const btn = document.getElementById('recommendBtn');
    const status = document.getElementById('recommendStatus');
    
    if (!url) {{
        status.innerHTML = '<span style="color: #ef4444;">请先输入网站地址</span>';
        return;
    }}
    
    btn.disabled = true;
    btn.textContent = '获取中...';
    status.innerHTML = '<span style="color: #667eea;">正在从Google Search Console获取推荐关键词...</span>';
    
    try {{
        const resp = await fetch(`/api/recommend_keywords?url=${{encodeURIComponent(url)}}`);
        const data = await resp.json();
        
        if (data.success && data.keywords && data.keywords.length > 0) {{
            // 将推荐关键词添加到当前关键词列表
            let added = 0;
            data.keywords.forEach(kw => {{
                if (!currentKeywords.includes(kw)) {{
                    currentKeywords.push(kw);
                    added++;
                }}
            }});
            
            renderKeywords();
            status.innerHTML = `<span style="color: #10b981;">✓ 成功添加 ${{added}} 个推荐关键词${{data.from_gsc ? '（来自GSC真实数据）' : '（模拟数据，配置GSC API后可获取真实数据）'}}</span>`;
        }} else if (data.keywords && data.keywords.length === 0) {{
            status.innerHTML = '<span style="color: #f59e0b;">未找到推荐关键词，请检查网站是否已添加到Google Search Console</span>';
        }} else {{
            status.innerHTML = `<span style="color: #ef4444;">获取失败: ${{data.error || '未知错误'}}</span>`;
        }}
    }} catch (err) {{
        status.innerHTML = `<span style="color: #ef4444;">网络错误: ${{err.message}}</span>`;
    }}
    
    btn.disabled = false;
    btn.textContent = '🔍 获取GSC推荐关键词';
}}

// ==================== 百度指数关键词推荐 ====================

let baiduRecommendations = [];

async function fetchBaiduRecommendations() {{
    const url = document.getElementById('siteUrl').value.trim();
    const btn = document.getElementById('baiduRecommendBtn');
    const status = document.getElementById('recommendStatus');
    const resultDiv = document.getElementById('baiduRecommendResult');
    
    if (!url) {{
        status.innerHTML = '<span style="color: #ef4444;">请先输入网站地址</span>';
        return;
    }}
    
    btn.disabled = true;
    btn.textContent = '分析中...';
    status.innerHTML = '<span style="color: #667eea;">正在基于行业词库分析推荐关键词...</span>';
    resultDiv.style.display = 'none';
    
    try {{
        const existingKws = currentKeywords.join(',');
        const resp = await fetch(`/api/baidu_recommend?url=${{encodeURIComponent(url)}}&existing=${{encodeURIComponent(existingKws)}}`);
        const data = await resp.json();
        
        if (data.success && data.recommendations && data.recommendations.length > 0) {{
            baiduRecommendations = data.recommendations;
            renderBaiduRecommendations();
            resultDiv.style.display = 'block';
            status.innerHTML = `<span style="color: #10b981;">✓ 找到 ${{data.recommendations.length}} 个推荐关键词，请选择添加</span>`;
        }} else {{
            status.innerHTML = '<span style="color: #f59e0b;">未找到推荐关键词，请尝试手动输入</span>';
        }}
    }} catch (err) {{
        status.innerHTML = `<span style="color: #ef4444;">网络错误: ${{err.message}}</span>`;
    }}
    
    btn.disabled = false;
    btn.textContent = '📊 百度指数关键词推荐';
}}

function renderBaiduRecommendations() {{
    const tbody = document.getElementById('baiduRecommendTable');
    let html = '';
    
    baiduRecommendations.forEach((rec, idx) => {{
        const trendColor = rec.trend === '上升' ? '#10b981' : (rec.trend === '下降' ? '#ef4444' : '#f59e0b');
        const volColor = rec.search_volume === '高' ? '#ef4444' : (rec.search_volume === '中' ? '#f59e0b' : '#10b981');
        const compColor = rec.competition === '高' ? '#ef4444' : (rec.competition === '中' ? '#f59e0b' : '#10b981');
        
        html += `<tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 8px; font-weight: 500;">${{rec.keyword}}</td>
            <td style="padding: 8px; text-align: center;"><span class="badge" style="background: #eef2ff; color: #667eea;">${{rec.category}}</span></td>
            <td style="padding: 8px; text-align: center; color: ${{volColor}}; font-weight: 600;">${{rec.search_volume}}</td>
            <td style="padding: 8px; text-align: center; color: ${{compColor}};">${{rec.competition}}</td>
            <td style="padding: 8px; text-align: center; color: ${{trendColor}};">${{rec.trend}}</td>
            <td style="padding: 8px; text-align: center;">
                <button type="button" class="btn btn-sm btn-primary" onclick="addBaiduKeyword(${{idx}})">添加</button>
            </td>
        </tr>
        <tr>
            <td colspan="6" style="padding: 0 8px 8px 8px; font-size: 0.8em; color: #888;">${{rec.reason}}</td>
        </tr>`;
    }});
    
    tbody.innerHTML = html;
}}

function addBaiduKeyword(idx) {{
    const rec = baiduRecommendations[idx];
    if (!currentKeywords.includes(rec.keyword)) {{
        currentKeywords.push(rec.keyword);
        renderKeywords();
        
        // 标记为已添加
        const btn = document.querySelectorAll('#baiduRecommendTable button')[idx];
        if (btn) {{
            btn.textContent = '已添加';
            btn.disabled = true;
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-gray');
        }}
    }}
}}
</script>

</body>
</html>"""

    # ==================== 服务器 ====================

    def start_server(self):
        """启动Web服务器"""
        dashboard = self

        class MultiUserHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path

                session_id = self._get_cookie('session_id')
                user_id = dashboard.sessions.get(session_id) if session_id else None

                if path == '/login':
                    self._send_html(dashboard.generate_login_page())

                elif path == '/register':
                    self._send_html(dashboard.generate_register_page())

                elif path == '/logout':
                    if session_id and session_id in dashboard.sessions:
                        del dashboard.sessions[session_id]
                    self._redirect('/login')

                elif path == '/' or path == '/dashboard':
                    if not user_id:
                        self._redirect('/login')
                        return
                    self._send_html(dashboard.generate_dashboard_page(user_id))

                elif path == '/api/stats':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    stats = dashboard._get_user_stats(user_id)
                    self._send_json(stats)

                elif path == '/api/websites':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    websites = dashboard._load_user_websites(user_id)
                    self._send_json({'websites': websites})

                elif path == '/api/user':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    user = user_manager.get_user_by_id(user_id)
                    if user:
                        self._send_json({
                            'username': user.username,
                            'email': user.email,
                            'plan': user.plan,
                            'max_websites': user.max_websites,
                            'max_daily_visits': user.max_daily_visits,
                            'api_key': user.api_key
                        })
                    else:
                        self._send_json({'error': '用户不存在'}, 404)

                elif path == '/api/rank':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    query_params = parse_qs(parsed_path.query)
                    engine = query_params.get('engine', [''])[0]
                    keyword = query_params.get('keyword', [''])[0]
                    domain = query_params.get('domain', [''])[0]
                    device = query_params.get('device', ['pc'])[0]
                    if not engine or not keyword or not domain:
                        self._send_json({'error': '缺少必要参数 (engine, keyword, domain)'}, 400)
                        return
                    result = dashboard._check_rank(keyword, domain, engine, device)
                    self._send_json(result)

                elif path == '/api/recommend_keywords':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    query_params = parse_qs(parsed_path.query)
                    url = query_params.get('url', [''])[0]
                    if not url:
                        self._send_json({'error': '缺少网站URL参数'}, 400)
                        return
                    
                    try:
                        # 检查GSC凭证状态
                        cred_status = gsc_recommender.check_credentials_setup()
                        
                        # 获取推荐关键词
                        keywords = gsc_recommender.get_recommended_keywords_for_site(url, limit=10)
                        
                        self._send_json({
                            'success': True,
                            'keywords': keywords,
                            'from_gsc': cred_status['configured'],
                            'message': '获取成功' if keywords else '未找到推荐关键词'
                        })
                    except Exception as e:
                        logger.error(f"获取推荐关键词失败: {e}")
                        self._send_json({'error': str(e), 'success': False, 'keywords': []})

                elif path == '/api/baidu_recommend':
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return
                    query_params = parse_qs(parsed_path.query)
                    url = query_params.get('url', [''])[0]
                    existing = query_params.get('existing', [''])[0]
                    
                    if not url:
                        self._send_json({'error': '缺少网站URL参数'}, 400)
                        return
                    
                    try:
                        # 解析已有关键词
                        existing_keywords = [kw.strip() for kw in existing.split(',') if kw.strip()]
                        
                        # 获取百度指数推荐
                        recommendations = baidu_recommender.get_recommendations(
                            url=url,
                            existing_keywords=existing_keywords,
                            limit=15
                        )
                        
                        # 转换为字典列表
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
                        
                        self._send_json({
                            'success': True,
                            'recommendations': recs_data,
                            'message': f'找到 {len(recs_data)} 个推荐关键词'
                        })
                    except Exception as e:
                        logger.error(f"获取百度指数推荐失败: {e}")
                        self._send_json({'error': str(e), 'success': False, 'recommendations': []})

                else:
                    self._send_html('<h1>404 - 页面不存在</h1>', 404)

            def do_POST(self):
                parsed_path = urlparse(self.path)
                path = parsed_path.path

                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')

                # 判断是否为JSON
                try:
                    params = json.loads(post_data)
                except (json.JSONDecodeError, ValueError):
                    params = parse_qs(post_data)

                if path == '/login':
                    if isinstance(params, dict) and 'username' in params:
                        username = params['username'] if isinstance(params['username'], str) else params.get('username', [''])[0]
                        password = params['password'] if isinstance(params['password'], str) else params.get('password', [''])[0]
                    else:
                        username = params.get('username', [''])[0]
                        password = params.get('password', [''])[0]

                    user = user_manager.login(username, password)
                    if user:
                        session_id = secrets.token_hex(16)
                        dashboard.sessions[session_id] = user.user_id
                        self._redirect('/dashboard', {'session_id': session_id})
                    else:
                        self._send_html(dashboard.generate_login_page('用户名或密码错误'))

                elif path == '/register':
                    if isinstance(params, dict) and 'username' in params:
                        username = params['username'] if isinstance(params['username'], str) else params.get('username', [''])[0]
                        email = params['email'] if isinstance(params['email'], str) else params.get('email', [''])[0]
                        password = params['password'] if isinstance(params['password'], str) else params.get('password', [''])[0]
                        password_confirm = params.get('password_confirm', '')
                        if isinstance(password_confirm, list):
                            password_confirm = password_confirm[0]
                    else:
                        username = params.get('username', [''])[0]
                        email = params.get('email', [''])[0]
                        password = params.get('password', [''])[0]
                        password_confirm = params.get('password_confirm', [''])[0]

                    if password != password_confirm:
                        self._send_html(dashboard.generate_register_page('两次输入的密码不一致'))
                        return
                    if len(password) < 6:
                        self._send_html(dashboard.generate_register_page('密码长度至少6位'))
                        return

                    user = user_manager.register(username, email, password)
                    if user:
                        session_id = secrets.token_hex(16)
                        dashboard.sessions[session_id] = user.user_id
                        self._redirect('/dashboard', {'session_id': session_id})
                    else:
                        self._send_html(dashboard.generate_register_page('用户名或邮箱已存在'))

                elif path == '/api/websites':
                    # JSON API: 保存网站列表
                    if not self._check_login():
                        self._send_json({'error': '未登录'}, 401)
                        return
                    session_id = self._get_cookie('session_id')
                    user_id = dashboard.sessions.get(session_id)
                    if not user_id:
                        self._send_json({'error': '未登录'}, 401)
                        return

                    try:
                        data = json.loads(post_data) if not isinstance(params, dict) or 'websites' not in str(params) else params
                        if isinstance(data, dict) and 'websites' in data:
                            websites = data['websites']
                        else:
                            websites = data if isinstance(data, list) else []
                    except Exception:
                        self._send_json({'error': '无效的数据格式'}, 400)
                        return

                    dashboard._save_user_websites(user_id, websites)
                    self._send_json({'success': True, 'message': '保存成功'})

                else:
                    self._send_html('<h1>404 - 页面不存在</h1>', 404)

            def _check_login(self) -> bool:
                session_id = self._get_cookie('session_id')
                return session_id and session_id in dashboard.sessions

            def _get_cookie(self, name: str) -> Optional[str]:
                cookie_header = self.headers.get('Cookie', '')
                cookies = {}
                for cookie in cookie_header.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        cookies[key] = value
                return cookies.get(name)

            def _send_html(self, html: str, status: int = 200, cookies: dict = None):
                self.send_response(status)
                if cookies:
                    for name, value in cookies.items():
                        self.send_header('Set-Cookie', f'{name}={value}; Path=/; HttpOnly')
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            def _send_json(self, data: dict, status: int = 200):
                self.send_response(status)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

            def _redirect(self, location: str, cookies: dict = None):
                self.send_response(302)
                self.send_header('Location', location)
                if cookies:
                    for name, value in cookies.items():
                        self.send_header('Set-Cookie', f'{name}={value}; Path=/; HttpOnly')
                self.end_headers()

            def log_message(self, format, *args):
                logger.info(f"Dashboard: {args[0]}")

        self.server = HTTPServer(('0.0.0.0', self.port), MultiUserHandler)

        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        logger.info(f"📊 多用户仪表盘已启动: http://0.0.0.0:{self.port}")

    def stop_server(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            logger.info("📊 多用户仪表盘已停止")


# 全局实例
multi_user_dashboard = MultiUserDashboard()
