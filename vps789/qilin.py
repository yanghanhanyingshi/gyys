from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("正在打开：api.uouin.com/cloudflare.html")
            page.goto(
                "https://api.uouin.com/cloudflare.html",
                wait_until="domcontentloaded",
                timeout=25000
            )

            print("等待优选IP表格加载...")
            page.wait_for_selector("#ipTable", timeout=25000)
            time.sleep(3)

            ip_data = []
            rows = page.query_selector_all("#ipTable tbody tr")

            # 遍历表格，提取 IP + 延迟
            for row in rows:
                ip_td = row.query_selector("td:nth-child(1)")
                ping_td = row.query_selector("td:nth-child(4)")

                if not ip_td or not ping_td:
                    continue

                ip = ip_td.inner_text().strip()
                ping_str = ping_td.inner_text().strip()

                # 过滤无效IP
                if not ip or "." not in ip:
                    continue

                # 提取延迟数字（过滤非数字、超时、异常值）
                try:
                    ping = int(''.join(filter(str.isdigit, ping_str)))
                except:
                    continue

                # 只保留 延迟 ≤ 300ms 的优质IP（可自己改数值）
                if ping <= 300:
                    ip_data.append((ip, ping))

            # 去重 + 按延迟从小到大排序
            ip_dict = {}
            for ip, ping in ip_data:
                if ip not in ip_dict:
                    ip_dict[ip] = ping

            # 排序：延迟越低越靠前
            sorted_ips = sorted(ip_dict.keys(), key=lambda x: ip_dict[x])

            # 保存到 qilin_ip.txt
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted_ips))

            print(f"✅ 抓取完成！去重+测速过滤后：{len(sorted_ips)} 个优质IP")

        except Exception as e:
            print(f"❌ 抓取失败：{str(e)}")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()
