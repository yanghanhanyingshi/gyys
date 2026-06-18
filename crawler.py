#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import time
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional

# --- 配置 ---
SOURCE_URL = "https://zip.cm.edu.kg/all.txt"
TIMEOUT = 5  # 连接超时时间（秒）
MAX_WORKERS = 30  # 并发测试线程数
OUTPUT_FILE_DETAIL = "valid_ips.txt"
OUTPUT_FILE_PURE = "valid_ips_pure.txt"
OUTPUT_FILE_JSON = "valid_ips.json"

# --- 日志函数 ---
def log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# --- 1. 获取IP列表 ---
def fetch_ips(url: str) -> List[str]:
    """从URL获取并解析IP:PORT列表"""
    try:
        log(f"正在从 {url} 获取数据...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 使用正则匹配 IP:PORT 格式 (忽略后面的#国家代码)
        pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d+\b'
        raw_ips = re.findall(pattern, response.text)
        
        # 去重并返回
        unique_ips = list(set(raw_ips))
        log(f"成功获取 {len(unique_ips)} 个独立IP")
        return unique_ips
    except requests.RequestException as e:
        log(f"获取IP列表失败: {e}", "ERROR")
        return []

# --- 2. 测试单个IP ---
def check_ip(ip_port: str) -> Tuple[Optional[str], Optional[float]]:
    """
    测试IP是否有效并测速
    返回: (有效的IP:PORT, 响应时间秒数) 或 (None, None)
    """
    url = f"http://{ip_port}"
    try:
        start_time = time.time()
        # 使用GET请求并设置stream=True，只读取头部以节省带宽
        response = requests.get(url, timeout=TIMEOUT, stream=True)
        response_time = time.time() - start_time
        
        # 如果状态码小于400，视为有效
        if response.status_code < 400:
            return ip_port, round(response_time, 3)
        return None, None
    except (requests.Timeout, requests.ConnectionError):
        return None, None
    except Exception:
        return None, None

# --- 3. 并发测试所有IP ---
def test_ips(ip_list: List[str]) -> List[Tuple[str, float]]:
    """并发测试所有IP，返回有效的(IP, 响应时间)列表"""
    if not ip_list:
        return []
    
    log(f"开始并发测试 {len(ip_list)} 个IP (使用 {MAX_WORKERS} 个线程)...")
    valid_results = []
    tested_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有测试任务
        future_to_ip = {executor.submit(check_ip, ip): ip for ip in ip_list}
        
        for future in as_completed(future_to_ip):
            tested_count += 1
            
            try:
                valid_ip, response_time = future.result()
                if valid_ip:
                    valid_results.append((valid_ip, response_time))
            except Exception as e:
                log(f"处理IP时发生异常: {e}", "ERROR")
            
            # 每处理100个或最后一个时输出进度
            if tested_count % 100 == 0 or tested_count == len(ip_list):
                log(f"测试进度: {tested_count}/{len(ip_list)}，当前有效: {len(valid_results)}")
    
    # 按响应时间排序（速度快的在前）
    valid_results.sort(key=lambda x: x[1])
    log(f"测试完成。有效IP: {len(valid_results)}，无效IP: {len(ip_list) - len(valid_results)}")
    return valid_results

# --- 4. 保存结果到文件 ---
def save_results(valid_ips: List[Tuple[str, float]]):
    """将有效IP列表保存到详细文件、纯IP文件和JSON文件"""
    if not valid_ips:
        log("没有有效的IP可以保存。", "WARNING")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 保存详细列表 (TXT)
    try:
        with open(OUTPUT_FILE_DETAIL, 'w', encoding='utf-8') as f:
            f.write(f"有效代理IP列表 - 更新时间: {timestamp}\n")
            f.write(f"总计: {len(valid_ips)} 个\n")
            f.write("-" * 50 + "\n")
            for i, (ip, speed) in enumerate(valid_ips, 1):
                f.write(f"{i:4d}. {ip}  (响应时间: {speed}s)\n")
        log(f"详细列表已保存至: {OUTPUT_FILE_DETAIL}")
    except IOError as e:
        log(f"保存详细文件失败: {e}", "ERROR")
    
    # 保存纯IP列表 (TXT)
    try:
        with open(OUTPUT_FILE_PURE, 'w', encoding='utf-8') as f:
            for ip, _ in valid_ips:
                f.write(f"{ip}\n")
        log(f"纯IP列表已保存至: {OUTPUT_FILE_PURE}")
    except IOError as e:
        log(f"保存纯IP文件失败: {e}", "ERROR")
    
    # 保存JSON格式
    try:
        json_data = [
            {
                "ip": ip,
                "response_time": speed,
                "timestamp": timestamp
            }
            for ip, speed in valid_ips
        ]
        with open(OUTPUT_FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        log(f"JSON数据已保存至: {OUTPUT_FILE_JSON}")
    except IOError as e:
        log(f"保存JSON文件失败: {e}", "ERROR")

# --- 5. 主运行函数 ---
def run_crawler():
    """执行一次完整的爬取和测试流程"""
    log("=" * 50)
    log("开始新的爬取任务")
    
    # 1. 获取IP
    raw_ips = fetch_ips(SOURCE_URL)
    if not raw_ips:
        log("任务终止：未获取到任何IP。")
        return
    
    # 2. 测试IP
    valid_ips = test_ips(raw_ips)
    
    # 3. 保存结果
    if valid_ips:
        save_results(valid_ips)
        # 显示前5个最快的IP
        log("最快的5个IP:")
        for i, (ip, speed) in enumerate(valid_ips[:5], 1):
            log(f"  {i}. {ip} - {speed}s")
    else:
        log("没有找到有效的IP。")
    
    log("任务完成。")
    log("=" * 50)

# --- 主程序入口 ---
if __name__ == "__main__":
    # 检查是否在GitHub Actions环境中
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    
    if is_github_actions:
        # GitHub Actions 自动运行
        log("GitHub Actions 模式 - 自动运行")
        run_crawler()
    else:
        # 本地运行模式
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
            # 定时运行模式 (每12小时)
            import schedule
            log("启动定时模式，每12小时运行一次。按 Ctrl+C 停止。")
            run_crawler()
            schedule.every(12).hours.do(run_crawler)
            while True:
                schedule.run_pending()
                time.sleep(60)
        else:
            # 单次运行模式
            run_crawler()
