import requests
import re
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
from typing import List, Dict, Set

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MultiIPCrawler:
    def __init__(self, config_file='config.json'):
        """
        初始化多源IP爬虫
        
        Args:
            config_file: 配置文件路径
        """
        self.config = self.load_config(config_file)
        self.urls = self.config.get('urls', [])
        self.timeout = self.config.get('timeout', 10)
        self.max_workers = self.config.get('max_workers', 30)
        self.output_file = self.config.get('output_file', 'valid_ips.txt')
        self.output_format = self.config.get('output_format', 'txt')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 存储所有IP
        self.all_ips: Set[str] = set()
        self.valid_ips: List[Dict] = []
        
        logger.info(f"初始化完成，共 {len(self.urls)} 个数据源")
        
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 默认配置
                default_config = {
                    "urls": ["https://zip.cm.edu.kg/all.txt"],
                    "timeout": 10,
                    "max_workers": 30,
                    "output_format": "txt",
                    "output_file": "valid_ips.txt"
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                logger.info(f"已创建默认配置文件: {config_file}")
                return default_config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {"urls": [], "timeout": 10, "max_workers": 30}
    
    def fetch_ips_from_url(self, url: str) -> List[str]:
        """
        从单个URL获取IP列表
        
        Args:
            url: 目标URL
            
        Returns:
            IP列表
        """
        try:
            logger.info(f"正在从 {url} 获取IP列表...")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析IP地址和端口
            # 支持多种格式: IP:PORT, IP PORT, IP, PORT
            patterns = [
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d+\b',  # IP:PORT
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\s+\d+\b',  # IP PORT
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'  # 仅IP
            ]
            
            ips = []
            for pattern in patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    if ':' in matches[0]:
                        # IP:PORT格式
                        ips.extend(matches)
                    elif ' ' in matches[0]:
                        # IP PORT格式，转换为IP:PORT
                        for match in matches:
                            parts = match.split()
                            if len(parts) == 2:
                                ips.append(f"{parts[0]}:{parts[1]}")
                    else:
                        # 仅IP格式，添加默认端口8080
                        for match in matches:
                            ips.append(f"{match}:8080")
            
            # 去重
            ips = list(set(ips))
            logger.info(f"从 {url} 获取到 {len(ips)} 个IP地址")
            return ips
            
        except requests.Timeout:
            logger.error(f"从 {url} 获取IP超时")
            return []
        except requests.RequestException as e:
            logger.error(f"从 {url} 获取IP失败: {e}")
            return []
        except Exception as e:
            logger.error(f"从 {url} 处理IP时出错: {e}")
            return []
    
    def fetch_all_ips(self) -> Set[str]:
        """
        从所有URL获取IP
        
        Returns:
            去重后的IP集合
        """
        all_ips = set()
        
        with ThreadPoolExecutor(max_workers=len(self.urls)) as executor:
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
                    logger.error(f"处理URL {url} 时出错: {e}")
        
        logger.info(f"从所有数据源共获取 {len(all_ips)} 个去重IP地址")
        return all_ips
    
    def check_ip_validity(self, ip: str) -> tuple:
        """
        检查IP是否有效
        
        Args:
            ip: IP地址（包含端口）
            
        Returns:
            (ip, is_valid, response_time)
        """
        try:
            # 测试HTTP协议
            url = f"http://{ip}"
            start_time = time.time()
            
            response = self.session.get(
                url, 
                timeout=self.timeout,
                allow_redirects=False,
                stream=True
            )
            response_time = time.time() - start_time
            
            # 检查响应状态码
            if response.status_code < 400:
                return ip, True, round(response_time, 3)
            else:
                return ip, False, None
                
        except requests.Timeout:
            return ip, False, None
        except requests.ConnectionError:
            return ip, False, None
        except Exception:
            return ip, False, None
    
    def test_ips(self, ips: Set[str]) -> List[Dict]:
        """
        并发测试多个IP
        
        Args:
            ips: IP集合
            
        Returns:
            有效的IP列表
        """
        valid_results = []
        invalid_count = 0
        total_ips = len(ips)
        
        if total_ips == 0:
            logger.warning("没有IP需要测试")
            return []
        
        logger.info(f"开始测试 {total_ips} 个IP地址，使用 {self.max_workers} 个线程...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_ip = {
                executor.submit(self.check_ip_validity, ip): ip 
                for ip in ips
            }
            
            processed = 0
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
                    
                    # 每处理100个IP显示进度
                    if processed % 100 == 0:
                        logger.info(f"进度: {processed}/{total_ips} "
                                  f"(有效: {len(valid_results)}, 无效: {invalid_count})")
                        
                except Exception as e:
                    logger.error(f"处理IP {ip} 时出错: {e}")
                    invalid_count += 1
        
        # 按响应时间排序
        valid_results.sort(key=lambda x: x['response_time'])
        
        logger.info(f"测试完成。有效IP: {len(valid_results)}，无效IP: {invalid_count}")
        return valid_results
    
    def save_to_txt(self, valid_ips: List[Dict], filename: str = None):
        """
        保存有效IP到TXT文件
        
        Args:
            valid_ips: 有效IP列表
            filename: 文件名
        """
        if filename is None:
            filename = self.output_file
        
        try:
            # 生成TXT格式内容
            content = []
            content.append("="*60)
            content.append(f"有效代理IP列表 - 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("="*60)
            content.append(f"总计: {len(valid_ips)} 个有效IP\n")
            
            for i, ip_info in enumerate(valid_ips, 1):
                content.append(f"{i}. {ip_info['ip']} (响应时间: {ip_info['response_time']}s)")
            
            content.append("\n" + "="*60)
            content.append(f"数据来源: {', '.join(self.urls)}")
            content.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 写入文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            logger.info(f"已保存 {len(valid_ips)} 个有效IP到 {filename}")
            
            # 同时保存纯IP列表（方便其他程序使用）
            pure_filename = filename.replace('.txt', '_pure.txt')
            with open(pure_filename, 'w', encoding='utf-8') as f:
                for ip_info in valid_ips:
                    f.write(f"{ip_info['ip']}\n")
            
            logger.info(f"已保存纯IP列表到 {pure_filename}")
            
        except Exception as e:
            logger.error(f"保存TXT文件失败: {e}")
    
    def save_to_json(self, valid_ips: List[Dict], filename: str = None):
        """
        保存有效IP到JSON文件（额外格式）
        
        Args:
            valid_ips: 有效IP列表
            filename: 文件名
        """
        if filename is None:
            filename = self.output_file.replace('.txt', '.json')
        
        try:
            # 加载已有的有效IP
            existing_ips = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_ips = json.load(f)
            
            # 合并并去重
            existing_dict = {item['ip']: item for item in existing_ips}
            for item in valid_ips:
                existing_dict[item['ip']] = item
            
            merged_ips = sorted(
                existing_dict.values(), 
                key=lambda x: x['response_time']
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(merged_ips, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已保存 {len(merged_ips)} 个有效IP到 {filename}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def run(self):
        """执行完整的爬取和测试流程"""
        start_time = time.time()
        
        logger.info("="*60)
        logger.info(f"开始多源IP爬取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        logger.info(f"数据源数量: {len(self.urls)}")
        for i, url in enumerate(self.urls, 1):
            logger.info(f"  {i}. {url}")
        logger.info("="*60)
        
        # 1. 从所有URL获取IP
        all_ips = self.fetch_all_ips()
        if not all_ips:
            logger.warning("没有获取到任何IP地址")
            return
        
        # 2. 测试IP有效性
        valid_ips = self.test_ips(all_ips)
        
        # 3. 保存结果
        if valid_ips:
            # 保存为TXT格式
            self.save_to_txt(valid_ips)
            
            # 同时保存JSON格式作为备份
            self.save_to_json(valid_ips)
            
            # 显示统计信息
            elapsed_time = time.time() - start_time
            logger.info("="*60)
            logger.info("任务完成统计:")
            logger.info(f"  总IP数: {len(all_ips)}")
            logger.info(f"  有效IP: {len(valid_ips)}")
            logger.info(f"  有效率: {len(valid_ips)/len(all_ips)*100:.2f}%")
            logger.info(f"  耗时: {elapsed_time:.2f} 秒")
            
            # 显示最快的10个IP
            logger.info("\n最快的10个IP:")
            for i, ip_info in enumerate(valid_ips[:10], 1):
                logger.info(f"  {i:2d}. {ip_info['ip']} - {ip_info['response_time']}s")
            
            logger.info("="*60)
        else:
            logger.warning("没有找到有效的IP地址")
        
        logger.info("任务结束\n")
    
    def run_scheduled(self, interval_hours=12):
        """
        定时运行爬虫
        
        Args:
            interval_hours: 间隔小时数
        """
        import schedule
        
        logger.info(f"启动定时任务，每 {interval_hours} 小时执行一次")
        
        # 立即执行一次
        self.run()
        
        # 设置定时任务
        schedule.every(interval_hours).hours.do(self.run)
        
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    """
    主函数
    """
    # 配置文件路径
    config_file = 'config.json'
    
    # 检查是否在GitHub Actions环境中
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        # GitHub Actions环境 - 自动运行
        crawler = MultiIPCrawler(config_file)
        crawler.run()
    else:
        # 本地环境 - 提供交互选项
        print("\n" + "="*60)
        print("多源IP爬虫工具")
        print("="*60)
        print("1. 单次运行")
        print("2. 定时运行 (每12小时)")
        print("3. 使用自定义配置")
        print("="*60)
        
        choice = input("请选择运行模式 (1-3): ").strip()
        
        if choice == "1":
            crawler = MultiIPCrawler(config_file)
            crawler.run()
        elif choice == "2":
            crawler = MultiIPCrawler(config_file)
            try:
                crawler.run_scheduled(12)
            except KeyboardInterrupt:
                logger.info("程序已手动停止")
        elif choice == "3":
            config_file = input("请输入配置文件路径 (默认: config.json): ").strip() or "config.json"
            crawler = MultiIPCrawler(config_file)
            crawler.run()
        else:
            print("无效选择")

if __name__ == "__main__":
    main()
