from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-images",
                "--disable-web-security",
                "--disable-features=IsolateOrigins",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        try:
            print("正在打开：api.uouin.com/cloudflare.html")

            page.goto(
                "https://api.uouin.com/cloudflare.html",
                wait_until="load",
                timeout=60000
            )

            # 等待页面动态加载IP数据（关键修复）
            print("等待IP数据加载...")
            time.sleep(8)

            ip_data = []
            rows = page.query_selector_all("div#ipTable table tbody tr")

            if not rows:
                rows = page.query_selector_all("div[contains(@class,'container')] table tbody tr")

            print(f"找到 {len(rows)} 行数据")

            for row in rows:
                tds = row.query_selector_all("td")
                if len(tds) < 4:
                    continue

                ip = tds[0].inner_text().strip()
                ping_str = tds[3].inner_text().strip()

                if not ip or "." not in ip:
                    continue

                # 提取延迟
                try:
                    ping = int(''.join(filter(str.isdigit, ping_str)))
                except:
                    ping = 9999

                # 只保留优质IP（延迟 ≤ 300ms）
                if ping <= 300:
                    ip_data.append((ip, ping))

            # 去重 + 排序（延迟低 → 高）
            ip_dict = {}
            for ip, ping in ip_data:
                if ip not in ip_dict:
                    ip_dict[ip] = ping

            sorted_ips = sorted(ip_dict.keys(), key=lambda x: ip_dict[x])

            # 保存
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted_ips))

            print(f"✅ 抓取完成！有效优质IP：{len(sorted_ips)} 个")

        except Exception as e:
            print(f"❌ 错误：{str(e)}")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()
