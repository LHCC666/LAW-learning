"""每日复习计划推送脚本 - 通过 Server酱 推送到微信"""
import urllib.request
import json
import sys
import os

# 读取配置
config_path = os.path.join(os.path.dirname(__file__), "study-push-config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

PUSH_URL = config["push_url"]

def push(title, content_file):
    """推送复习指南到微信"""
    with open(content_file, "r", encoding="utf-8") as f:
        desp = f.read()

    data = {
        "title": title,
        "desp": desp
    }

    req = urllib.request.Request(
        PUSH_URL,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        if result.get("code") == 0:
            print(f"[OK] 推送成功: {title}")
        else:
            print(f"[FAIL] 推送失败: {result}")
        return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python push_study.py <标题> <内容文件路径>")
        sys.exit(1)

    title = sys.argv[1]
    content_file = sys.argv[2]
    push(title, content_file)
