#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
from typing import List, Dict, Set, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IPProxyCrawler:
    """IP代理爬虫类"""
    
    def __init__(self, config_file='config.json'):
        """初始化爬虫"""
        self.config = self.load_config(config_file)
        self.urls = self.config.get('urls', [])
        self.timeout = self.config.get('timeout', 10)
        self.max_workers = self.config.get('max_workers', 30)
        self.output_file = self.config.get('output_file', 'valid_ips.txt')
        
        # 初始化会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 存储数据
        self.all_ips = set()
        self.valid_ips = []
        
        logger.info(f"✅ 爬虫初始化完成，数据源: {len(self.urls)} 个")
    
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"✅ 加载配置文件: {config_file}")
                return config
            else:
                # 创建默认配置
                default_config = {
                    "urls": [
                        "https://zip.cm.edu.kg/all.txt",
                        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all.txt",
                        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
                    ],
                    "timeout": 10,
                    "max_workers": 30,
                    "output_file": "valid_ips.txt"
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ 创建默认配置文件: {config_file}")
                return default_config
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            return {"urls": [], "timeout": 10, "max_workers": 30}
    
    def fetch_ips_from_url(self, url: str) -> List[str]:
        """从单个URL获取IP列表"""
        try:
            logger.info(f"  📥 正在获取: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析IP地址和端口
            # 匹配 IP:PORT 或 IP PORT 格式
            patterns = [
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d+\b',  # IP:PORT
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\s+\d+\b'   # IP PORT
            ]
            
            ips = []
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if ':' in match:
                        ips.append(match)
                    elif ' ' in match:
                        parts = match.split()
                        if len(parts) == 2:
                            ips.append(f"{parts[0]}:{parts[1]}")
            
            # 如果没找到带端口的，尝试只提取IP
            if not ips:
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                ips = re.findall(ip_pattern, response.text)
                # 添加默认端口
                ips = [f"{ip}:8080" for ip in ips]
            
            # 去重
            ips = list(set(ips))
            logger.info(f"  ✅ 从 {url} 获取到 {len(ips)} 个IP")
            return ips
            
        except requests.Timeout:
            logger.warning(f"  ⚠️ 从 {url} 获取IP超时")
            return []
        except Exception as e:
            logger.warning(f"  ⚠️ 从 {url} 获取IP失败: {e}")
            return []
    
    def fetch_all_ips(self) -> Set[str]:
        """从所有URL获取IP"""
        logger.info("🔄 开始获取所有数据源...")
        
        all_ips = set()
        with ThreadPoolExecutor(max_workers=min(len(self.urls), 10)) as executor:
            future_to_url = {
                executor.submit(self.fetch_ips_from_url, url): url 
                for url in self.urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    ips = future.result()
                    all_ips.update(ips)
                except Exception as e:
                    logger.error(f"❌ 处理URL {url} 时出错: {e}")
        
        logger.info(f"✅ 共获取 {len(all_ips)} 个去重IP地址")
        return all_ips
    
    def check_ip_validity(self, ip: str) -> Tuple[str, bool, float]:
        """检查IP是否有效并测速"""
        try:
            url = f"http://{ip}"
            start_time = time.time()
            
            response = self.session.get(
                url, 
                timeout=self.timeout,
                allow_redirects=False,
                stream=True
            )
            response_time = time.time() - start_time
            
            if response.status_code < 400:
                return ip, True, round(response_time, 3)
            return ip, False, None
            
        except Exception:
            return ip, False, None
    
    def test_ips(self, ips: Set[str]) -> List[Dict]:
        """并发测试多个IP"""
        total_ips = len(ips)
        if total_ips == 0:
            logger.warning("⚠️ 没有IP需要测试")
            return []
        
        logger.info(f"🔄 开始测试 {total_ips} 个IP (并发数: {self.max_workers})...")
        
        valid_results = []
        invalid_count = 0
        processed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_ip_validity, ip): ip 
                for ip in ips
            }
            
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    ip_addr, is_valid, response_time = future.result()
                    processed += 1
                    
                    if is_valid:
                        valid_results.append({
                            'ip': ip_addr,
                            'response_time': response_time,
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        invalid_count += 1
                    
                    # 每100个显示进度
                    if processed % 100 == 0:
                        logger.info(f"  📊 进度: {processed}/{total_ips} "
                                  f"(有效: {len(valid_results)}, 无效: {invalid_count})")
                        
                except Exception as e:
                    logger.error(f"❌ 处理IP {ip} 时出错: {e}")
                    invalid_count += 1
        
        # 按响应时间排序
        valid_results.sort(key=lambda x: x['response_time'])
        
        logger.info(f"✅ 测试完成! 有效: {len(valid_results)}, 无效: {invalid_count}")
        return valid_results
    
    def save_results(self, valid_ips: List[Dict]):
        """保存结果到多种格式"""
        if not valid_ips:
            logger.warning("⚠️ 没有有效IP可保存")
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 保存详细TXT
        try:
            content = []
            content.append("="*70)
            content.append(f"🌐 有效代理IP列表")
            content.append(f"📅 更新时间: {timestamp}")
            content.append("="*70)
            content.append(f"📊 总计: {len(valid_ips)} 个有效IP\n")
            
            for i, ip_info in enumerate(valid_ips, 1):
                content.append(f"{i:4d}. {ip_info['ip']}  (响应: {ip_info['response_time']}s)")
            
            content.append("\n" + "="*70)
            content.append(f"📌 数据源: {len(self.urls)} 个")
            content.append(f"⚡ 测试耗时: {self.timeout}s 超时")
            content.append("="*70)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            logger.info(f"✅ 保存详细列表: {self.output_file}")
            
        except Exception as e:
            logger.error(f"❌ 保存TXT失败: {e}")
        
        # 2. 保存纯IP列表
        try:
            pure_file = self.output_file.replace('.txt', '_pure.txt')
            with open(pure_file, 'w', encoding='utf-8') as f:
                for ip_info in valid_ips:
                    f.write(f"{ip_info['ip']}\n")
            logger.info(f"✅ 保存纯IP列表: {pure_file}")
        except Exception as e:
            logger.error(f"❌ 保存纯IP列表失败: {e}")
        
        # 3. 保存JSON
        try:
            json_file = self.output_file.replace('.txt', '.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(valid_ips, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 保存JSON数据: {json_file}")
        except Exception as e:
            logger.error(f"❌ 保存JSON失败: {e}")
    
    def run(self):
        """执行爬取任务"""
        start_time = time.time()
        
        logger.info("="*70)
        logger.info("🚀 开始IP代理爬取任务")
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)
        logger.info(f"📌 数据源数量: {len(self.urls)}")
        for i, url in enumerate(self.urls, 1):
            logger.info(f"  {i}. {url}")
        logger.info("="*70)
        
        # 1. 获取所有IP
        all_ips = self.fetch_all_ips()
        if not all_ips:
            logger.error("❌ 没有获取到任何IP地址")
            return
        
        # 2. 测试IP
        valid_ips = self.test_ips(all_ips)
        
        # 3. 保存结果
        if valid_ips:
            self.save_results(valid_ips)
            
            elapsed = time.time() - start_time
            logger.info("="*70)
            logger.info("📊 任务完成统计:")
            logger.info(f"  📥 总IP数: {len(all_ips)}")
            logger.info(f"  ✅ 有效IP: {len(valid_ips)}")
            logger.info(f"  📈 有效率: {len(valid_ips)/len(all_ips)*100:.2f}%")
            logger.info(f"  ⏱️  耗时: {elapsed:.2f} 秒")
            
            # 显示最快的10个
            logger.info(f"\n🏆 最快的10个IP:")
            for i, ip_info in enumerate(valid_ips[:10], 1):
                logger.info(f"  {i:2d}. {ip_info['ip']} - {ip_info['response_time']}s")
            
            logger.info("="*70)
        else:
            logger.warning("⚠️ 没有找到有效的IP地址")
        
        logger.info("✅ 任务结束\n")

def main():
    """主函数"""
    # 检查是否在GitHub Actions环境
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_github:
        # GitHub Actions自动运行
        logger.info("🔄 GitHub Actions 模式")
        crawler = IPProxyCrawler()
        crawler.run()
    else:
        # 本地交互模式
        print("\n" + "="*70)
        print("🌐 多源IP代理爬虫 v2.0")
        print("="*70)
        print("1. 🚀 单次运行")
        print("2. 🔄 定时运行 (每12小时)")
        print("3. ⚙️  自定义配置")
        print("="*70)
        
        choice = input("请选择 (1-3): ").strip()
        
        if choice == "1":
            crawler = IPProxyCrawler()
            crawler.run()
        elif choice == "2":
            import schedule
            crawler = IPProxyCrawler()
            logger.info("🔄 启动定时任务 (每12小时)")
            crawler.run()
            schedule.every(12).hours.do(crawler.run)
            while True:
                schedule.run_pending()
                time.sleep(60)
        elif choice == "3":
            config_file = input("配置文件路径 (默认: config.json): ").strip() or "config.json"
            crawler = IPProxyCrawler(config_file)
            crawler.run()
        else:
            print("❌ 无效选择")

if __name__ == "__main__":
    main()
