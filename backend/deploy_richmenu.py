"""
智慧宮廟 LINE 官方圖文選單 (Rich Menu) 自動發布腳本
功能：
1. 自動讀取 .env 中的 LINE_CHANNEL_ACCESS_TOKEN
2. 建立標準 2500 x 1686 六宮格圖文選單物件
3. 上傳 assets/richmenu_smart_temple.png
4. 設定為所有信眾預設開啟的圖文選單
"""

import os
import json
import urllib.request
import urllib.error

# 讀取 .env
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
env_vars = {}
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

TOKEN = env_vars.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../assets/richmenu_smart_temple.png"))

# 六宮格座標與點擊行為定義 (2500 x 1686)
# 單格寬度 833 / 834，高度 843
RICH_MENU_SCHEMA = {
    "size": {
        "width": 2500,
        "height": 1686
    },
    "selected": True,
    "name": "智慧宮廟六宮格文化圖文選單",
    "chatBarText": "🏮 點此開啟宮廟功能選單",
    "areas": [
        # 1. 左上：線上靈籤 (LIFF 搖筒抽籤與請示)
        {
            "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "uri",
                "label": "線上靈籤",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv?page=divination"
            }
        },
        # 2. 中上：正念冥想 (3D 立體念珠撥珠)
        {
            "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
            "action": {
                "type": "uri",
                "label": "正念冥想",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv?page=meditation"
            }
        },
        # 3. 右上：參拜足跡 (精選香路與 GPS 導航)
        {
            "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "uri",
                "label": "參拜足跡",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv?page=routes"
            }
        },
        # 4. 左下：祈安點燈 (線上光明燈與公益認捐)
        {
            "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
            "action": {
                "type": "uri",
                "label": "祈安點燈",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv?page=lighting"
            }
        },
        # 5. 中下：信眾中心 (生肖歲煞排盤與白米收驚)
        {
            "bounds": {"x": 833, "y": 843, "width": 834, "height": 843},
            "action": {
                "type": "uri",
                "label": "信眾中心",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv?page=profile"
            }
        },
        # 6. 右下：大殿首頁 (宮廟大殿首頁與敬神儀軌)
        {
            "bounds": {"x": 1667, "y": 843, "width": 833, "height": 843},
            "action": {
                "type": "uri",
                "label": "大殿首頁",
                "uri": "https://liff.line.me/2011668576-3Qay1nBv"
            }
        }
    ]
}

def deploy():
    if not TOKEN:
        print("[ERROR] 未在 .env 找到 LINE_CHANNEL_ACCESS_TOKEN，請檢查設定。")
        return

    if not os.path.exists(IMAGE_PATH):
        print(f"[ERROR] 找不到圖文選單圖片：{IMAGE_PATH}")
        return

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    # 1. 建立 Rich Menu
    print("1. 正在向 LINE 建立圖文選單結構...")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/richmenu",
        data=json.dumps(RICH_MENU_SCHEMA).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rich_menu_id = data.get("richMenuId")
            print(f"   [OK] 圖文選單建立成功，ID: {rich_menu_id}")
    except urllib.error.HTTPError as e:
        print(f"   [FAIL] 建立失敗: {e.code} - {e.read().decode('utf-8')}")
        return

    # 2. 上傳圖文選單圖片
    print(f"2. 正在上傳圖片 ({IMAGE_PATH})...")
    with open(IMAGE_PATH, "rb") as img_file:
        img_bytes = img_file.read()

    upload_headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "image/png"
    }
    upload_url = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
    req_upload = urllib.request.Request(upload_url, data=img_bytes, headers=upload_headers, method="POST")

    try:
        with urllib.request.urlopen(req_upload) as resp:
            print("   [OK] 圖片上傳成功！")
    except urllib.error.HTTPError as e:
        print(f"   [FAIL] 上傳圖片失敗: {e.code} - {e.read().decode('utf-8')}")
        return

    # 3. 設為官方預設圖文選單
    print(f"3. 正在設定為全體用戶預設選單...")
    default_url = f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}"
    req_default = urllib.request.Request(default_url, headers={"Authorization": f"Bearer {TOKEN}"}, method="POST")

    try:
        with urllib.request.urlopen(req_default) as resp:
            print(f"   [SUCCESS] 圖文選單已成功發布並設為預設！")
            print(f"   現在開啟手機 LINE 與【智慧宮廟】聊天，即可看見全新圖文選單！")
    except urllib.error.HTTPError as e:
        print(f"   [FAIL] 設定預設選單失敗: {e.code} - {e.read().decode('utf-8')}")

if __name__ == "__main__":
    deploy()
