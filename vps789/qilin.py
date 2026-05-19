from playwright.sync_api import sync_playwright
import re
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
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print("正在打开页面...")
            page.goto("https://api.uouin.com/cloudflare.html", timeout=60000)
            
            # 关键：多重等待，确保内容加载
            print("等待内容加载...")
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_selector("table", timeout=20000)   # 等待表格出现
            time.sleep(3)  # 再等一小会儿
            
            # 获取页面全部文本
            page_text = page.inner_text("body")
            
            # 提取 IPv4
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            all_ips = ip_pattern.findall(page_text)
            
            valid_ips = []
            for ip in all_ips:
                parts = ip.split(".")
                if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                    valid_ips.append(ip)
            
            unique_ips = sorted(list(set(valid_ips)))
            
            # 保存
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")
            
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(unique_ips))
            
            print(f"✅ 抓取完成！共获取 {len(unique_ips)} 个IPv4")
            if len(unique_ips) > 0:
                print(f"前5个示例: {unique_ips[:5]}")
            print(f"文件路径：{save_path}")
            
        except Exception as e:
            print(f"❌ 错误：{str(e)}")
            # 调试输出
            try:
                page.screenshot(path="debug_error.png")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("已保存 debug_error.png 和 debug_page.html，请检查")
            except:
                pass
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()
