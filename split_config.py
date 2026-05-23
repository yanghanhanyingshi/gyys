import requests
import os
import base64

# 固定头部订阅信息
fixed_text = """#profile-title: base64:8J+GkyBHaXRodWIgfCBCYXJyeS1mYXIg8J+ltw==
#profile-update-interval: 1
#subscription-userinfo: upload=29; download=12; total=10737418240000000; expire=2546249531
#support-url: https://github.com/barry-far/V2ray-config
#profile-web-page-url: https://github.com/barry-far/V2ray-config
"""

# GitHub Actions 固定工作目录，改用仓库根目录
root_path = os.getcwd()
split_dir = os.path.join(root_path, "Splitted-By-Protocol")

# 自动创建拆分文件夹（不存在则新建）
os.makedirs(split_dir, exist_ok=True)

# 定义各协议文件路径
vmess_file = os.path.join(split_dir, "vmess.txt")
vless_file = os.path.join(split_dir, "vless.txt")
trojan_file = os.path.join(split_dir, "trojan.txt")
ss_file = os.path.join(split_dir, "ss.txt")
ssr_file = os.path.join(split_dir, "ssr.txt")

# 初始化清空文件
for file_path in [vmess_file, vless_file, trojan_file, ss_file, ssr_file]:
    open(file_path, "w", encoding="utf-8").close()

# 初始化节点字符串
vmess_content = ""
vless_content = ""
trojan_content = ""
ss_content = ""
ssr_content = ""

# 本地配置文件路径
local_config_file = os.path.join(root_path, "All_Configs_Sub.txt")
response_text = ""

# 读取本地文件，无则拉取远程源
if os.path.exists(local_config_file):
    try:
        with open(local_config_file, "r", encoding="utf-8") as f:
            response_text = f.read()
    except Exception as e:
        print(f"本地文件读取失败，切换远程源：{str(e)}")
        try:
            resp = requests.get(
                "https://raw.githubusercontent.com/barry-far/V2ray-config/main/All_Configs_Sub.txt",
                timeout=15
            )
            resp.raise_for_status()
            response_text = resp.text
        except Exception as err:
            print(f"远程订阅获取失败：{str(err)}")
else:
    try:
        resp = requests.get(
            "https://raw.githubusercontent.com/barry-far/V2ray-config/main/All_Configs_Sub.txt",
            timeout=15
        )
        resp.raise_for_status()
        response_text = resp.text
    except Exception as err:
        print(f"远程订阅获取失败：{str(err)}")

# 按协议分类节点
for line in response_text.splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith("vmess"):
        vmess_content += line + "\n"
    elif line.startswith("vless"):
        vless_content += line + "\n"
    elif line.startswith("trojan"):
        trojan_content += line + "\n"
    elif line.startswith("ssr"):
        ssr_content += line + "\n"
    elif line.startswith("ss"):
        ss_content += line + "\n"

# 写入分类后的订阅文件
with open(vmess_file, "w", encoding="utf-8") as f:
    f.write(fixed_text + vmess_content)

with open(vless_file, "w", encoding="utf-8") as f:
    f.write(fixed_text + vless_content)

with open(trojan_file, "w", encoding="utf-8") as f:
    f.write(fixed_text + trojan_content)

with open(ss_file, "w", encoding="utf-8") as f:
    f.write(fixed_text + ss_content)

with open(ssr_file, "w", encoding="utf-8") as f:
    f.write(fixed_text + ssr_content)

print("✅ 节点拆分完成，已保存至 Splitted-By-Protocol 目录")
