import requests
import os
import time

# 订阅头部固定信息
fixed_text = """#profile-title: base64:8J+GkyBHaXRodWIgfCBCYXJyeS1mYXIg8J+ltw==
#profile-update-interval: 1
#subscription-userinfo: upload=29; download=12; total=10737418240000000; expire=2546249531
#support-url: https://github.com/barry-far/V2ray-config
#profile-web-page-url: https://github.com/barry-far/V2ray-config
"""

# 仓库根目录
root_path = os.getcwd()
split_dir = os.path.join(root_path, "Splitted-By-Protocol")
os.makedirs(split_dir, exist_ok=True)

# 协议文件路径
file_map = {
    "vmess": os.path.join(split_dir, "vmess.txt"),
    "vless": os.path.join(split_dir, "vless.txt"),
    "trojan": os.path.join(split_dir, "trojan.txt"),
    "ss": os.path.join(split_dir, "ss.txt"),
    "ssr": os.path.join(split_dir, "ssr.txt")
}

# 清空旧文件
for fp in file_map.values():
    with open(fp, "w", encoding="utf-8") as f:
        f.write("")

# 初始化内容容器
content = {"vmess": "", "vless": "", "trojan": "", "ss": "", "ssr": ""}

# 读取本地文件，不存在则拉取远程源
local_cfg = os.path.join(root_path, "All_Configs_Sub.txt")
raw_text = ""

if os.path.exists(local_cfg):
    try:
        with open(local_cfg, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except:
        pass

if not raw_text.strip():
    try:
        res = requests.get(
            "https://raw.githubusercontent.com/barry-far/V2ray-config/main/All_Configs_Sub.txt",
            timeout=20
        )
        res.raise_for_status()
        raw_text = res.text
    except Exception as e:
        print(f"数据源获取失败：{e}")

# 按协议分类解析
for line in raw_text.splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith("vmess"):
        content["vmess"] += line + "\n"
    elif line.startswith("vless"):
        content["vless"] += line + "\n"
    elif line.startswith("trojan"):
        content["trojan"] += line + "\n"
    elif line.startswith("ssr"):
        content["ssr"] += line + "\n"
    elif line.startswith("ss"):
        content["ss"] += line + "\n"

# 写入分类文件
for proto, fp in file_map.items():
    with open(fp, "w", encoding="utf-8") as f:
        f.write(fixed_text + content[proto])

print("✅ 节点拆分执行完成")
