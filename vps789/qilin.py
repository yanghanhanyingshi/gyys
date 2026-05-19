from playwright.sync_api import sync_playwright
import re
import json
import os
import time

IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')


def extract_ips(text):
    ips = IP_PATTERN.findall(text)

    valid = []
    for ip in ips:
        parts = ip.split(".")
        if all(0 <= int(x) <= 255 for x in parts):
            valid.append(ip)

    return valid


def run():
    all_ips = set()

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,  # Cloudflare 建议关闭无头
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 900}
        )

        page = context.new_page()

        # ======================================
        # 监听所有网络响应
        # ======================================
        def handle_response(response):
            try:
                url = response.url

                # 只处理 API / JSON
                if (
                    "api" in url
                    or "json" in url
                    or response.request.resource_type == "xhr"
                ):

                    text = response.text()

                    ips = extract_ips(text)

                    if ips:
                        print(f"发现IP接口: {url}")
                        print(f"提取到 {len(ips)} 个IP")

                        for ip in ips:
                            all_ips.add(ip)

            except Exception:
                pass

        page.on("response", handle_response)

        try:
            print("打开页面...")

            page.goto(
                "https://api.uouin.com/cloudflare.html",
                wait_until="networkidle",
                timeout=120000
            )

            # 等待动态加载
            time.sleep(15)

            # ======================================
            # 再从页面兜底提取一次
            # ======================================
            body_text = page.locator("body").inner_text()

            body_ips = extract_ips(body_text)

            for ip in body_ips:
                all_ips.add(ip)

            print(f"\n最终获取 IP 数量: {len(all_ips)}")

            # 保存文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(all_ips)))

            print(f"已保存: {save_path}")

        except Exception as e:
            print("错误:", str(e))

        finally:
            browser.close()


if __name__ == "__main__":
    run()
