"""
Web统计仪表盘 - 提供HTML可视化统计报告
"""

import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from urllib.parse import parse_qs, urlparse
from loguru import logger

from .config_manager import config
from .monitor import DailyStats


class StatsDashboard:
    """统计仪表盘"""
    
    def __init__(self, stats_dir: str = "stats", port: int = 8080):
        self.stats_dir = Path(stats_dir)
        self.port = port
        self.server = None
        self.server_thread = None
    
    def get_all_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取最近N天的统计数据"""
        stats_list = []
        
        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            stats_file = self.stats_dir / f"{target_date.isoformat()}.json"
            
            if stats_file.exists():
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        stats_list.append(data)
                except Exception as e:
                    logger.error(f"读取统计文件失败 {stats_file}: {e}")
        
        return stats_list
    
    def get_website_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取各网站的统计汇总"""
        all_stats = self.get_all_stats(days)
        
        website_summary = {}
        total_summary = {
            "total_visits": 0,
            "successful_visits": 0,
            "failed_visits": 0,
            "total_duration": 0
        }
        
        for day_stats in all_stats:
            total_summary["total_visits"] += day_stats.get("total_visits", 0)
            total_summary["successful_visits"] += day_stats.get("successful_visits", 0)
            total_summary["failed_visits"] += day_stats.get("failed_visits", 0)
            total_summary["total_duration"] += day_stats.get("total_duration", 0)
            
            websites = day_stats.get("websites", {})
            for url, site_data in websites.items():
                if url not in website_summary:
                    website_summary[url] = {
                        "total_visits": 0,
                        "successful_visits": 0,
                        "failed_visits": 0,
                        "total_duration": 0
                    }
                
                website_summary[url]["total_visits"] += site_data.get("total_visits", 0)
                website_summary[url]["successful_visits"] += site_data.get("successful_visits", 0)
                website_summary[url]["failed_visits"] += site_data.get("failed_visits", 0)
                website_summary[url]["total_duration"] += site_data.get("total_duration", 0)
        
        return {
            "summary": total_summary,
            "websites": website_summary,
            "days": days
        }
    
    def generate_html_report(self) -> str:
        """生成HTML统计报告"""
        stats = self.get_website_stats(days=7)
        
        # 计算成功率
        total = stats["summary"]["total_visits"]
        success = stats["summary"]["successful_visits"]
        success_rate = (success / total * 100) if total > 0 else 0
        
        # 生成网站表格行
        website_rows = ""
        for url, data in sorted(stats["websites"].items(), key=lambda x: x[1]["total_visits"], reverse=True):
            site_total = data["total_visits"]
            site_success = data["successful_visits"]
            site_rate = (site_success / site_total * 100) if site_total > 0 else 0
            avg_duration = data["total_duration"] / site_total if site_total > 0 else 0
            
            website_rows += f"""
                <tr>
                    <td class="url" title="{url}">{url[:50]}{'...' if len(url) > 50 else ''}</td>
                    <td class="number">{site_total}</td>
                    <td class="number success">{site_success}</td>
                    <td class="number error">{data['failed_visits']}</td>
                    <td class="number">{site_rate:.1f}%</td>
                    <td class="number">{avg_duration:.1f}s</td>
                </tr>
            """
        
        # 获取最近30天数据用于图表
        daily_data = self.get_all_stats(days=30)
        chart_labels = []
        chart_visits = []
        chart_success = []
        
        for day_data in reversed(daily_data):
            chart_labels.append(day_data.get("date", "")[5:])  # 只显示月-日
            chart_visits.append(day_data.get("total_visits", 0))
            chart_success.append(day_data.get("successful_visits", 0))
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Traffic Bot - 统计仪表盘</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card h3 {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-card.success .value {{ color: #10b981; }}
        .stat-card.error .value {{ color: #ef4444; }}
        .stat-card.warning .value {{ color: #f59e0b; }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .chart-container h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        
        .table-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        
        .table-container h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        
        th {{
            background: #f8fafc;
            font-weight: 600;
            color: #475569;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        tr:hover {{
            background: #f8fafc;
        }}
        
        .number {{
            text-align: center;
            font-weight: 600;
        }}
        
        .success {{ color: #10b981; }}
        .error {{ color: #ef4444; }}
        
        .url {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .refresh-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 1.5em;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
        }}
        
        .refresh-btn:hover {{
            background: #5a67d8;
            transform: scale(1.1);
        }}
        
        .update-time {{
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-top: 20px;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            header h1 {{
                font-size: 1.8em;
            }}
            
            .stat-card .value {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 SEO Traffic Bot</h1>
            <p>网站流量统计仪表盘 - 最近7天数据</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>总访问次数</h3>
                <div class="value">{stats['summary']['total_visits']}</div>
            </div>
            <div class="stat-card success">
                <h3>成功访问</h3>
                <div class="value">{stats['summary']['successful_visits']}</div>
            </div>
            <div class="stat-card error">
                <h3>失败访问</h3>
                <div class="value">{stats['summary']['failed_visits']}</div>
            </div>
            <div class="stat-card warning">
                <h3>成功率</h3>
                <div class="value">{success_rate:.1f}%</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>📈 每日访问趋势 (最近30天)</h2>
            <canvas id="visitChart" height="100"></canvas>
        </div>
        
        <div class="table-container">
            <h2>🌐 各网站访问详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>网站URL</th>
                        <th class="number">总访问</th>
                        <th class="number">成功</th>
                        <th class="number">失败</th>
                        <th class="number">成功率</th>
                        <th class="number">平均停留</th>
                    </tr>
                </thead>
                <tbody>
                    {website_rows}
                </tbody>
            </table>
        </div>
        
        <p class="update-time">最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()" title="刷新">↻</button>
    
    <script>
        const ctx = document.getElementById('visitChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {chart_labels},
                datasets: [{{
                    label: '总访问',
                    data: {chart_visits},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }}, {{
                    label: '成功访问',
                    data: {chart_success},
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def start_server(self):
        """启动Web服务器"""
        class DashboardHandler(BaseHTTPRequestHandler):
            dashboard = self
            
            def do_GET(self):
                parsed_path = urlparse(self.path)
                
                if parsed_path.path == '/' or parsed_path.path == '/index.html':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    html = self.dashboard.generate_html_report()
                    self.wfile.write(html.encode('utf-8'))
                
                elif parsed_path.path == '/api/stats':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    stats = self.dashboard.get_website_stats()
                    self.wfile.write(json.dumps(stats, ensure_ascii=False).encode('utf-8'))
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                logger.info(f"Dashboard: {args[0]}")
        
        self.server = HTTPServer(('0.0.0.0', self.port), DashboardHandler)
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"📊 统计仪表盘已启动: http://0.0.0.0:{self.port}")
    
    def stop_server(self):
        """停止Web服务器"""
        if self.server:
            self.server.shutdown()
            logger.info("📊 统计仪表盘已停止")


# 全局仪表盘实例
dashboard = StatsDashboard()
