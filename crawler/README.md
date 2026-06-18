# 多源IP爬虫工具

自动从多个数据源爬取和验证代理IP地址，支持多格式输出，每12小时自动运行一次。

## 功能特点

- ✅ 支持多URL数据源
- ✅ 自动去重IP地址
- ✅ 并发测试IP可用性
- ✅ 测速并排序
- ✅ 输出TXT格式（包含详细信息）
- ✅ 输出纯IP列表（便于其他程序使用）
- ✅ 输出JSON格式（完整数据）
- ✅ 定时自动运行（GitHub Actions）
- ✅ 支持手动触发
- ✅ 配置文件管理

## 目录结构
crawler/
├── .github/
│ └── workflows/
│ └── ip_crawler.yml # GitHub Actions配置
├── crawler.py # 主程序
├── config.json # 配置文件
├── requirements.txt # 依赖
├── valid_ips.txt # 有效IP（详细）
├── valid_ips_pure.txt # 有效IP（纯列表）
├── valid_ips.json # 有效IP（JSON格式）
└── crawler.log # 运行日志

## 配置文件 (config.json)

```json
{
  "urls": [
    "https://zip.cm.edu.kg/all.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
  ],
  "timeout": 10,
  "max_workers": 30,
  "output_format": "txt",
  "output_file": "valid_ips.txt"
}
配置说明
urls: IP数据源URL列表（支持多个）

timeout: 测试超时时间（秒）

max_workers: 并发测试线程数

output_format: 输出格式（txt/json）

output_file: 输出文件名

输出格式
1. valid_ips.txt (详细信息)
============================================================
有效代理IP列表 - 更新时间: 2026-06-18 10:30:00
============================================================
总计: 45 个有效IP

1. 192.168.1.1:8080 (响应时间: 0.123s)
2. 192.168.1.2:8080 (响应时间: 0.156s)
...

============================================================
数据来源: https://zip.cm.edu.kg/all.txt
测试时间: 2026-06-18 10:30:00

2. valid_ips_pure.txt (纯IP列表)
192.168.1.1:8080
192.168.1.2:8080

3. valid_ips.json (JSON格式)
[
  {
    "ip": "192.168.1.1:8080",
    "response_time": 0.123,
    "timestamp": "2026-06-18T10:30:00"
  }
]

