import os
import sys
import time
import base64
import random
import traceback
import collections
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, FollowEvent
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="靈籤入微 - AI 智慧宮廟後端 Webhook", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 即時日誌快取（記錄最近 100 筆系統動作，方便診斷）
SERVER_LOGS = collections.deque(maxlen=100)

def log_event(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{now}] {msg}"
    SERVER_LOGS.append(entry)
    print(entry, flush=True)

# 環境變數設定（請於 Render 後台或本地 .env 設定，嚴禁在公開代碼中硬編碼）
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct").strip()

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    max_retries=1,
    timeout=25.0
)

# 智慧宮廟線上服務處 客服專員 System Prompt
TEMPLE_SERVICE_PROMPT = """你是「靈籤入微 - 智慧宮廟線上服務處」的官方首席智能執事與文化導覽員。你具備深厚豐富的台灣宮廟文化、傳統禮俗、民間信仰、神明歷史與籤詩解析底蘊。
請以客觀、莊重、親切、敬虔且具備專業客服素養的語氣，為信士提供詳盡、準確且富有文化溫度的解答。請一律使用【繁體中文】回答。

【宮廟文化核心知識庫】：
1. 【台中萬春宮（原名藍興宮）】：
   - 歷史沿革：創建於清康熙末年（1721年），為台中市中區歷史最悠久的開基名剎，俗稱「台中媽祖」或「大墩媽祖」。總兵藍廷珍恭迎湄洲媽祖聖像隨軍渡海來台，於大墩街初建「藍興宮」，後於光緒年間重建定名為「萬春宮」。
   - 主祀神明：【天上聖母 湄洲媽祖】（大墩媽祖）。
   - 配祀神明：觀音佛祖、註生娘娘、福德正神、文昌帝君、關聖帝君、千里眼將軍、順風耳將軍、虎爺將軍等。
   - 珍貴文物與特色：道光年間青斗石獅、清代光緒皇帝御賜「光被四表」古匾、山川殿精緻剪黏與木雕藝術。

2. 【標準宮廟參拜順序（六步驟）】：
   - 第一步【淨身洗手・正冠脫帽】：端正心念，洗淨雙手。
   - 第二步【龍進虎出・不踏門檻】：面對廟門由「右側龍門進（進吉），左側虎門出（出凶）」，切忌由中門（神明通道）進出或踩踏門檻。
   - 第三步【敬拜天公（玉皇上帝）】：先至天公爐前，面朝外天公，持香三拜，報上信士姓名、農曆生辰、現居地址，後插香一至三炷。
   - 第四步【正殿敬拜主神】：進正殿誠心向主神敬拜，清楚稟報今日祈求事項（一事一問、具體清晰）。
   - 第五步【依序敬拜配祀各殿】：遵循由左至右、由尊至卑、正殿至後殿原則，依序參拜各殿神尊與桌下虎爺將軍。
   - 第六步【祈福過爐・燒化金帛】：平安符於主爐順時針繞三圈（過爐過火）獲得加持，後添敬香油或燒化金帛。

3. 【智慧宮廟線上服務與近期活動】：
   - 📿【湄洲媽靈籤（六十甲子靈籤）】：誠心搖筒、三聖筊請示神意，並提供 AI 深度客觀解籤（ https://liff.line.me/2011668576-3Qay1nBv?page=divination ）。
   - 🏮【祈安點燈專區】：提供文昌光明燈、元辰斗燈、祈安燭火線上祈福與文教公益（ https://liff.line.me/2011668576-3Qay1nBv?page=lighting ）。
   - 🧘【正念冥想・檀木佛珠】：3D 立體斜角檀木佛珠，金光呼吸引導、捻珠積福、沉澱心靈（ https://liff.line.me/2011668576-3Qay1nBv?page=meditation ）。
   - ⛩️【參拜足跡巡禮】：收錄開基名剎、身邊中小宮廟、舊城商圈走讀等實體 Touch 感應打卡收集數位香火袋（ https://liff.line.me/2011668576-3Qay1nBv?page=routes ）。
   - 🌾【信眾中心（白米收驚與生肖歲煞）】：安撫心神不寧、查詢流年太歲與歲煞制化指南（ https://liff.line.me/2011668576-3Qay1nBv?page=profile ）。

【回覆規範】：
- 稱呼用戶為「信士」或「您」。
- 回覆結構條理分明（可用項目清單）、重點突出、語意完整，結尾劃上適當標點符號。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 模型，具備多模型層級降級防線與超時防護"""
    is_fortune = any(k in user_message for k in ["靈籤", "籤詩", "第", "首", "聖筊"])
    max_tok = 700 if is_fortune else 450

    # 候選可用模型清單 (優先 Llama 3.2 11B Multimodal)
    candidate_models = [
        NVIDIA_MODEL,
        "mistralai/mistral-nemotron",
        "nvidia/ising-calibration-1.5-31b"
    ]

    for model_name in candidate_models:
        try:
            response = nvidia_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": TEMPLE_SERVICE_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=max_tok,
                timeout=16.0
            )
            msg = response.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", "")
            if content and content.strip():
                return content.strip()
        except Exception as e:
            log_event(f"NVIDIA 模型 [{model_name}] 異常或超時 ({e})，嘗試切換下一模型")

    return get_casual_fallback(user_message)


def identify_quick_intent(user_text: str) -> str:
    """高頻專用意圖精準秒回引擎 (0.01 秒無延遲，不受第三方 AI 佇列或超時影響)"""
    t = user_text.strip().lower()

    # 1. 台中萬春宮 / 藍興宮 / 供奉神明 / 歷史特色查詢
    if any(k in t for k in ["萬春宮", "藍興宮", "台中媽祖", "大墩媽祖", "供奉什麼神", "主祀神明", "供奉神明", "主神是誰", "萬春宮歷史", "道光石獅"]):
        return (
            "🏮【台中萬春宮（原名藍興宮）神明與文化底蘊】：\n\n"
            "📌【主祀神明】：天上聖母 湄洲媽祖（尊稱「台中媽祖」或「大墩媽祖」）。\n\n"
            "📌【配祀神明】：觀音佛祖、註生娘娘、文昌帝君、福德正神、關聖帝君、千里眼將軍、順風耳將軍、虎爺將軍。\n\n"
            "🏛️【歷史由來】：創建於清康熙末年（1721年），為台中市區最古老的開基媽祖名剎。由總兵藍廷珍恭迎湄洲媽祖渡海來台，於大墩街設廟，後重建定名「萬春宮」。\n\n"
            "✨【鎮宮之寶】：\n"
            "1. 🦁【道光青斗石獅】：殿前極具歷史工藝價值之清代青斗石獅。\n"
            "2. 📜【光被四表古匾】：清光緒皇帝御賜重要歷史古匾。\n\n"
            "👉 歡迎點選下方選單「參拜足跡」展開舊城名剎走讀，或至「線上靈籤」虔誠向湄洲媽祖請示！"
        )

    # 2. 參拜流程 / 參拜順序 / 拜拜指南 / 參拜儀軌 (對應圖文選單右下角)
    if any(k in t for k in ["參拜流程", "參拜順序", "拜拜流程", "拜拜順序", "參拜指南", "拜拜指南", "如何拜拜", "怎麼拜拜", "怎麼拜", "進廟順序", "參拜儀軌", "拜拜禮儀", "持香", "拜拜小撇步", "參拜小撇步", "天公爐", "龍進虎出"]):
        return (
            "🏮【宮廟參拜傳統標準儀軌（六大步驟）】：\n\n"
            "1. 💧【淨身端正】：洗淨雙手、脫帽正冠，收攝心神。\n\n"
            "2. 🚪【龍進虎出】：面對廟門，由「右側龍門進、左側虎門出」（象徵入吉出凶），切勿踐踏門檻或走中央神明中門。\n\n"
            "3. 👑【先敬天公】：至天公爐前持香朝外向玉皇上帝敬拜，報上信士姓名、農曆生辰、現居地址，後插天公爐。\n\n"
            "4. 🪔【正殿主神】：入正殿敬拜主神（如湄洲媽祖），誠心稟明所求（一事一問、具體清晰）。\n\n"
            "5. 🕊️【配祀各殿】：依序由左至右、由尊至卑參拜後殿及各殿配祀神明，最後向桌下虎爺將軍行禮。\n\n"
            "6. 📿【過爐祈安】：將隨身平安符或香火袋於主爐上方「順時針繞三圈」獲得神明靈氣護佑。\n\n"
            "👉 若欲線上向神明祈願，可點選下方「湄洲媽靈籤」或「正念冥想」！"
        )

    # 3. 近期活動 / 線上服務 / 廟務說明
    if any(k in t for k in ["近期活動", "最新活動", "有什麼活動", "活動有哪些", "宮廟活動", "線上服務", "廟務", "功能", "智慧宮廟有什麼"]):
        return (
            "🏮【智慧宮廟線上服務處・當前五大活動與服務】：\n\n"
            "1. 📿【湄洲媽靈籤】：搖筒請示六十甲子靈籤與 AI 深度客觀解籤\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=divination\n\n"
            "2. 🏮【祈安點燈專區】：文昌光明、元辰祿位祈福與公益認捐\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=lighting\n\n"
            "3. 🧘【正念冥想・檀木佛珠】：3D 金光呼吸定心捻珠、累積每日功德\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=meditation\n\n"
            "4. ⛩️【參拜足跡巡禮】：開基名剎與舊城走讀，實體感應打卡收集香火袋\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=routes\n\n"
            "5. 🌾【信眾中心（收驚與歲煞）】：白米收驚安魂與生肖流年太歲制化指南\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=profile\n\n"
            "信士可直接點擊上方連結或下方圖文選單隨時體驗！"
        )

    # 4. 智慧廟祝 / 官方助理介紹 (對應圖文選單中下角)
    if any(k in t for k in ["智慧廟祝", "廟祝", "你是誰", "你的功能", "你會做什麼", "信眾中心", "助理"]):
        return (
            "信士您好！我是「智慧宮廟線上服務處」的數位文化執事與智慧廟祝。\n\n"
            "本線上服務處隨時為信士提供五大文化服務：\n"
            "1. 📿【湄洲媽靈籤】：六十甲子靈籤與 AI 深度解籤\n"
            "2. 🧘【正念冥想】：3D 斜角立體檀木捻珠與呼吸定心\n"
            "3. 🏮【祈安點燈】：文昌光明、元辰祈安與功德祿位\n"
            "4. ⛩️【參拜足跡】：宮廟名剎行腳打卡與數位香火袋收集\n"
            "5. 🌾【白米收驚與生肖歲煞】：安魂定神與流年太歲制化諮詢\n\n"
            "請問今日有什麼事項需要為您向神明指引或查詢嗎？"
        )

    # 5. 正念冥想 / 佛珠 / 捻珠
    if any(k in t for k in ["正念冥想", "冥想", "佛珠", "捻珠", "念珠", "定心", "靜心", "積福"]):
        return (
            "🧘【正念冥想・檀木佛珠】：\n\n"
            "以 3D 擬真崖柏檀木佛珠搭配金光呼吸引導，每一次撥動佛珠皆為自己與家人累積功德福報，助您撫平焦慮、安神定心。\n\n"
            "👉 點此入座體驗正念冥想：\n"
            "https://liff.line.me/2011668576-3Qay1nBv?page=meditation"
        )

    # 6. 祈安點燈
    if any(k in t for k in ["祈安點燈", "點燈", "光明燈", "文昌燈", "太歲燈", "元辰燈"]):
        return (
            "🏮【祈安點燈專區】：\n\n"
            "供奉殿前宮燈斗燈與元辰燭火，祈求文昌智慧、財運亨通、闔家平安。\n\n"
            "👉 點此開啟線上點燈專區：\n"
            "https://liff.line.me/2011668576-3Qay1nBv?page=lighting"
        )

    # 7. 收驚與生肖歲煞
    if any(k in t for k in ["收驚", "白米收驚", "生肖歲煞", "太歲", "犯太歲", "沖煞", "心神不寧", "避邪"]):
        return (
            "🌾【信眾中心・白米收驚與生肖歲煞】：\n\n"
            "若近日感到心神不寧、睡眠難安，可透過白米收驚指引安魂定魄；亦可查詢流年犯太歲之生肖歲煞化解之道。\n\n"
            "👉 點此前往信眾中心：\n"
            "https://liff.line.me/2011668576-3Qay1nBv?page=profile"
        )

    # 8. 意圖偵測：求籤 / 抽籤 / 擲筊 (且非已抽到之籤詩)
    fortune_intent = any(k in t for k in ["求籤", "抽籤", "擲筊", "聖筊", "想抽", "想求", "抽個籤", "問事", "請示神明", "抽籤網站", "靈籤"])
    has_drawn_poem = any(k in t for k in ["詩曰", "【靈籤", "第", "首", "大吉", "上吉", "中吉", "中平"])
    if fortune_intent and not has_drawn_poem:
        return (
            "信士您好，若欲向湄洲媽祖祈願請示靈籤，請移步至智慧宮廟線上求籤專區：\n"
            "👉 https://liff.line.me/2011668576-3Qay1nBv?page=divination\n\n"
            "【求籤指引】：心念姓名、農曆生辰與明確問事內容（一事一問），搖動籤筒後需連續擲得「三個聖杯」方為應允正籤。求得籤詩後可回傳聊天室為您深度客觀解析。"
        )

    # 9. 情緒宣洩 / 粗話 / 負面低潮心靈安撫
    if any(k in t for k in ["幹", "靠", "操", "三小", "白痴", "爛", "煩", "累", "痛", "哭", "難過", "生氣", "氣死", "好衰", "倒楣", "壓力", "心煩"]):
        return (
            "信士請寬心消氣。人生旅途如潮水起伏，難免遇逢波折、委屈與鬱悶，神明慈悲，知曉信士心中不易。\n\n"
            "不妨先做幾次深呼吸、放鬆雙肩。若心中有未解的結或困惑，隨時可點選下方「正念冥想」靜心捻珠，或於「線上靈籤」虔誠請示神意提點。\n\n"
            "心平則氣和，定能化險為夷、撥雲見日。願神明垂慈庇佑您安康自在！"
        )

    # 10. 日常招呼與基本確認
    if any(k in t for k in ["哈囉", "嗨", "hi", "hello", "早安", "晚安", "午安", "你好", "在嗎", "在不在", "欸", "有人嗎", "在", "你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話", "理我"]):
        return random.choice([
            "信士您好，歡迎光臨智慧宮廟線上服務處！請問今日有什麼能為您引導或服務的地方嗎？",
            "信士吉祥。線上服務處隨時為您提供參拜儀軌諮詢、線上求籤與各項廟務指引。",
            "您好！智慧宮廟客服系統正常運作中，願神明保佑您身心康泰、諸事順遂。"
        ])

    return None


def get_casual_fallback(user_text: str) -> str:
    """智能情境客觀保底庫（依據問題語境給予實質宮廟文化與儀軌解答）"""
    t = user_text.lower()
    # 1. 萬春宮 / 媽祖 / 宮廟歷史 / 主神
    if any(k in t for k in ["萬春宮", "藍興宮", "媽祖", "供奉", "主神", "主祀", "配祀", "神明", "石獅", "大墩"]):
        return (
            "🏮【台中萬春宮神明與文化底蘊介紹】：\n\n"
            "📌【主祀神明】：天上聖母 湄洲媽祖（尊稱「台中媽祖」或「大墩媽祖」）。\n\n"
            "📌【配祀神明】：觀音佛祖、註生娘娘、文昌帝君、福德正神、關聖帝君、千里眼將軍、順風耳將軍、虎爺將軍。\n\n"
            "🏛️【歷史由來】：創建於清康熙末年（1721年），為台中市區最古老的開基媽祖名剎。總兵藍廷珍恭迎湄洲媽祖渡海來台，於大墩街設廟，後定名「萬春宮」。\n\n"
            "✨【重要文物】：清代道光青斗石獅與光緒皇帝御賜「光被四表」古匾。\n\n"
            "👉 歡迎點選下方選單「參拜足跡」展開巡禮，或至「湄洲媽靈籤」虔誠向神明請示！"
        )
    # 2. 參拜流程 / 順序 / 拜拜
    elif any(k in t for k in ["參拜", "拜拜", "流程", "順序", "儀軌", "怎麼拜", "如何拜", "持香", "天公爐", "進廟"]):
        return (
            "🏮【宮廟參拜標準六大步驟與傳統儀軌】：\n\n"
            "1. 💧【淨身端正】：洗淨雙手、脫帽正冠，收攝心神。\n\n"
            "2. 🚪【龍進虎出】：面對廟門由「右側龍門進、左側虎門出」（入吉出凶），切勿踏門檻或走神明中門。\n\n"
            "3. 👑【先敬天公】：至天公爐前面朝外向玉皇上帝敬拜，報上信士姓名、農曆生辰、現居地址，後插天公爐。\n\n"
            "4. 🪔【正殿主神】：入正殿誠心敬拜主神（如湄洲媽祖），一事一問、具體清晰。\n\n"
            "5. 🕊️【配祀各殿】：依序由左至右、由尊至卑參拜後殿各殿配祀神明，最後向桌下虎爺將軍行禮。\n\n"
            "6. 📿【祈福過爐】：隨身平安符或香火袋於主爐上方「順時針繞三圈」獲得神明靈氣加持。\n\n"
            "👉 若欲線上向神明祈願，可點選下方「湄洲媽靈籤」或「正念冥想」！"
        )
    # 3. 近期活動 / 服務 / 功能
    elif any(k in t for k in ["活動", "服務", "功能", "近期", "最新", "有哪些"]):
        return (
            "🏮【智慧宮廟線上服務處・當前五大活動與服務】：\n\n"
            "1. 📿【湄洲媽靈籤】：線上搖筒抽六十甲子靈籤與 AI 深度客觀解籤\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=divination\n\n"
            "2. 🏮【祈安點燈】：文昌光明、元辰斗燈線上祈福與公益認捐\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=lighting\n\n"
            "3. 🧘【正念冥想】：3D 檀木佛珠金光呼吸引導、定心積福\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=meditation\n\n"
            "4. ⛩️【參拜足跡】：開基名剎與舊城走讀，實體感應打卡收集數位香火袋\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=routes\n\n"
            "5. 🌾【信眾中心】：白米收驚安魂與生肖流年太歲制化指南\n"
            "   👉 https://liff.line.me/2011668576-3Qay1nBv?page=profile\n\n"
            "信士可直接點擊上方連結或下方圖文選單隨時體驗！"
        )
    # 4. 求籤 / 籤詩 / 解籤 / 運勢
    elif any(k in t for k in ["籤", "運勢", "未來", "事業", "感情", "功名", "問事"]):
        return (
            "信士您好，若欲請示近期運勢或指引迷津，建議可前往「湄洲媽靈籤」專區誠心搖筒請示神明：\n"
            "👉 https://liff.line.me/2011668576-3Qay1nBv?page=divination\n\n"
            "【求籤要訣】：默念姓名生辰與具體問事（一事一問），擲得三聖筊確認籤枝，求得籤詩後可回傳此處為您客觀解析。"
        )
    return (
        "信士您好，智慧宮廟線上服務處隨時為您提供參拜儀軌諮詢、線上靈籤求請、祈安點燈、正念冥想與名廟文化導覽。"
        "請問今日有什麼具體事項需要為您向神明請示或引導嗎？"
    )


def process_and_reply(user_text: str, reply_token: str, user_id: str):
    """在背景非同步處理訊息並透過 LINE 送出"""
    t_start = time.time()
    log_event(f"收到信徒 [{user_id}] 訊息: {user_text}")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        try:
            if user_id:
                messaging_api.show_loading_animation(
                    ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=5)
                )
        except Exception:
            pass

        # 1. 優先透過高頻意圖秒回引擎 (0.01 秒即時回覆，絕不超時)
        quick_reply = identify_quick_intent(user_text)
        if quick_reply:
            reply_content = quick_reply
        else:
            # 2. 特殊或自由問答，調用 NVIDIA AI 進行客觀深度解答
            reply_content = call_nvidia_ai(user_text)

        elapsed = time.time() - t_start
        log_event(f"回覆生成完成 (耗時 {elapsed:.2f}s): {reply_content[:25]}...")

        # 優先 reply_message，失敗自動轉 push_message
        sent_success = False
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )
            log_event(f"已成功透過 reply_message 回傳訊息！")
            sent_success = True
        except Exception as err:
            log_event(f"reply_message 失敗 ({err})，嘗試 push_message 保底...")

        if not sent_success and user_id:
            try:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=reply_content)]
                    )
                )
                log_event(f"已成功透過 push_message 發送給信徒 [{user_id}]！")
            except Exception as push_err:
                log_event(f"push_message 亦失敗: {push_err}")


def call_nvidia_vision(image_b64: str) -> str:
    """調用 NVIDIA NIM 視覺模型辨識照片（智慧宮廟客服文化導覽與客觀解說）"""
    timeout_sec = 16.0
    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是智慧宮廟線上服務處的官方智能客服人員。信士傳送了一張照片（可能包含籤詩、神明聖像、平安符、香火袋或廟宇建築）。"
                        "請以客觀、禮貌、專業且莊重的客服語氣，用繁體中文為信士說明照片中的宗教文物象徵意義、文化由來與正向安定的提醒，篇幅適中、條理清晰，結尾語意完整。"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "客服人員您好，這是我拍的照片，請協助解讀與說明："},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=750,
            timeout=timeout_sec
        )
        msg = response.choices[0].message
        content = msg.content or getattr(msg, "reasoning_content", "")
        if content and content.strip():
            return content.strip()
    except Exception as e:
        log_event(f"視覺辨識略過或超時 ({e})")

    return "信士您好，已收到您傳送的照片。若此為靈籤或平安符，神明庇佑心誠則靈；若需進一步問事或解籤，歡迎隨時於對話框留言，本處竭誠為您服務。"


def process_and_reply_image(message_id: str, reply_token: str, user_id: str):
    """在背景非同步讀取 LINE 照片並透過視覺模型進行辨識與解籤"""
    t_start = time.time()
    log_event(f"收到信徒 [{user_id}] 傳送照片 (訊息 ID: {message_id})")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)

        try:
            if user_id:
                messaging_api.show_loading_animation(
                    ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=8)
                )
        except Exception:
            pass

        try:
            img_bytes = blob_api.get_message_content(message_id)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            reply_content = call_nvidia_vision(img_b64)
        except Exception as e:
            log_event(f"讀取照片失敗: {e}")
            reply_content = "哎呀照片讀取有點小問題，不過心誠則靈！有想問的事阿伯都在這裡陪你聊聊～"

        elapsed = time.time() - t_start
        log_event(f"照片視覺辨識回覆完成 (耗時 {elapsed:.2f}s): {reply_content[:25]}...")

        sent_success = False
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )
            log_event("已成功透過 reply_message 回傳照片辨識結果！")
            sent_success = True
        except Exception as err:
            log_event(f"照片 reply 失敗 ({err})，嘗試 push_message 保底...")

        if not sent_success and user_id:
            try:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=reply_content)]
                    )
                )
                log_event(f"已成功透過 push_message 發送照片分析給信徒 [{user_id}]！")
            except Exception as push_err:
                log_event(f"照片 push 亦失敗: {push_err}")


# 暫存信徒抽籤結果（用於尚未加好友時，加好友瞬間立即自動補推籤詩與解籤）
PENDING_FORTUNES = {}
# 防重複推播快取（防止同用戶在短時間內重複收到相同籤詩）
LAST_PUSHED_FORTUNES = {}


def handle_follow_event(user_id: str):
    """信徒加入好友時的專屬迎賓與抽籤補推流程"""
    log_event(f"信徒 [{user_id}] 成功加入【智慧宮廟】為好友！")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        # 檢查該用戶是否有 1 小時內剛抽得之靈籤
        pending = PENDING_FORTUNES.pop(user_id, None)
        if pending and (time.time() - pending.get("timestamp", 0) < 3600):
            fortune_text = pending.get("text", "")
            # 若 45 秒內已發過完全相同的籤詩，避免重複推送
            last_push = LAST_PUSHED_FORTUNES.get(user_id)
            if last_push and (time.time() - last_push.get("timestamp", 0) < 45) and (last_push.get("text") == fortune_text):
                log_event(f"信徒 [{user_id}] 剛已推播過該籤詩，略過加好友重複推播")
                return

            welcome_text = (
                "🎉 感謝信士加入【智慧宮廟】！\n\n"
                "已自動為您送達剛剛在線上求籤專區所獲賜的神明靈籤："
            )
            try:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[
                            TextMessage(text=welcome_text),
                            TextMessage(text=fortune_text)
                        ]
                    )
                )
                log_event(f"已成功於加好友瞬間補推靈籤給信徒 [{user_id}]！")
                LAST_PUSHED_FORTUNES[user_id] = {"text": fortune_text, "timestamp": time.time()}
                process_and_push_ai_interpretation(fortune_text, user_id)
            except Exception as e:
                log_event(f"加好友補推靈籤失敗: {e}")
        else:
            welcome_msg = (
                "🏮 信士吉祥！歡迎光臨「靈籤入微 - 智慧宮廟文化生活圈」官方服務處。\n\n"
                "點擊下方圖文選單，隨時體驗：\n"
                "1. 📿【線上靈籤】：誠心搖筒請示六十甲子靈籤與 AI 客觀解籤\n"
                "2. 🧘【正念冥想】：3D 斜角立體捻珠與累積今日功德\n"
                "3. ⛩️【參拜腳印】：四大名廟巡禮路線與實體感應打卡\n"
                "4. 💡【祈安點燈】：文昌光明與元辰祈安文教公益\n"
                "5. 📜【參拜指南】：隨時查詢進廟順序與持香撇步\n\n"
                "願神明威靈護佑，祈願所求皆得圓滿、平安吉祥！"
            )
            try:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=welcome_msg)]
                    )
                )
            except Exception as e:
                log_event(f"推送迎賓詞失敗: {e}")


def process_and_push_ai_interpretation(fortune_text: str, user_id: str):
    """為抽籤的信徒，非同步生成官方宮廟客觀解籤並推播至 LINE 聊天室"""
    time.sleep(1.2)  # 稍微錯開，讓籤詩先抵達聊天室
    log_event(f"正在為信徒 [{user_id}] 生成官方宮廟客觀解籤...")
    reply_content = call_nvidia_ai(fortune_text)
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        try:
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=reply_content)]
                )
            )
            log_event(f"已成功推送 AI 解籤給信徒 [{user_id}]！")
        except Exception as e:
            log_event(f"推送 AI 解籤失敗: {e}")


@app.post("/api/push_fortune")
async def api_push_fortune(request: Request, background_tasks: BackgroundTasks):
    """供電腦版/外開瀏覽器/手機 LIFF 一鍵將抽籤結果送回用戶 LINE 聊天室"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user_id = data.get("user_id")
    text = data.get("text")
    if not user_id or not text:
        raise HTTPException(status_code=400, detail="Missing user_id or text")

    log_event(f"收到抽籤回傳請求: 信徒 [{user_id}]")
    PENDING_FORTUNES[user_id] = {"text": text, "timestamp": time.time()}

    # 防重複發送機制（45 秒內同用戶相同內容不重複推播）
    last_push = LAST_PUSHED_FORTUNES.get(user_id)
    if last_push and (time.time() - last_push.get("timestamp", 0) < 45) and (last_push.get("text") == text):
        log_event(f"信徒 [{user_id}] 45 秒內重複請求推播相同籤詩，已阻擋重複發送！")
        return {
            "status": "success",
            "delivered": True,
            "duplicate_blocked": True,
            "message": "籤詩已送達，請勿重複發送"
        }

    is_delivered = False
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        try:
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)]
                )
            )
            log_event(f"已成功將籤詩推播至信徒 [{user_id}] 聊天室！")
            is_delivered = True
            LAST_PUSHED_FORTUNES[user_id] = {"text": text, "timestamp": time.time()}
            background_tasks.add_task(process_and_push_ai_interpretation, text, user_id)
        except Exception as e:
            log_event(f"推播籤詩失敗 (可能尚未加好友): {e}")

    return {
        "status": "success",
        "delivered": is_delivered,
        "message": "已成功將籤詩送達您的 LINE 聊天室" if is_delivered else "籤詩已暫存，加好友後將自動送達"
    }


@app.post("/api/interpret_fortune")
async def api_interpret_fortune(request: Request):
    """直接在網頁畫面上進行官方宮廟即時客觀解籤（適用於不想跳轉 LINE 的電腦用戶）"""
    data = await request.json()
    text = data.get("text", "")
    quick = identify_quick_intent(text)
    if quick:
        reply = quick
    else:
        reply = call_nvidia_ai(text)
    return {"status": "success", "reply": reply}


@app.post("/api/touch_checkin")
async def api_touch_checkin(request: Request):
    """供 LINE Touch 實體碰觸感應時，記錄打卡並自動推送 LINE 官方打卡憑證"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user_id = data.get("user_id")
    route_id = data.get("route_id", "wenchang")
    try:
        cp_index = int(data.get("checkpoint_index", 0))
    except (ValueError, TypeError):
        cp_index = 0

    TEMPLE_NAMES = {
        "wenchang": ["台北文昌宮 (雙連)", "大龍峒保安宮文昌殿", "新莊文昌祠"],
        "yuelao": ["台北霞海城隍廟", "艋舺龍山寺月老廳", "大稻埕慈聖宮"],
        "mazu": ["北投關渡宮", "松山慈祐宮", "士林慈諴宮"],
        "baishatun": ["白沙屯拱天宮", "通霄慈惠宮", "北港朝天宮"]
    }
    names = TEMPLE_NAMES.get(route_id, ["宮廟"])
    temple_name = names[cp_index] if 0 <= cp_index < len(names) else names[0]

    log_event(f"信徒 [{user_id}] 透過 LINE Touch 實體感應完成【{temple_name}】打卡！")

    # 透過 LINE Messaging API 自動推送專屬數位香火憑證
    if user_id and LINE_CHANNEL_ACCESS_TOKEN:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)
            push_text = (
                f"🎉【LINE Touch 實體感應打卡成功】\n\n"
                f"恭賀信士親臨參拜【{temple_name}】！\n"
                f"已為您成功蓋印第 {cp_index + 1} 枚數位足跡。\n"
                f"神尊威靈護佑，祈願所求皆遂、平安吉祥！\n\n"
                f"👉 點此開啟參拜足跡進度地圖：\n"
                f"https://liff.line.me/2011668576-3Qay1nBv?route={route_id}"
            )
            try:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=push_text)]
                    )
                )
                log_event(f"已成功推送 LINE Touch 憑證給信徒 [{user_id}]！")
            except Exception as e:
                log_event(f"推送 Touch 憑證失敗: {e}")

    return {
        "status": "success",
        "route_id": route_id,
        "checkpoint_index": cp_index,
        "temple_name": temple_name,
        "message": f"已成功記錄【{temple_name}】LINE Touch 足跡"
    }


@app.get("/api/maps_key")
def get_maps_key():
    """安全提供受網域限制之 Google Maps API Key"""
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return {"status": "ok", "key": key}


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "chat_style": "temple-customer-service-objective",
        "vision_support": "multimodal-enabled",
        "desktop_push_support": "api-push-fortune-enabled",
        "logs_endpoint": "/logs",
        "version": "3.0.0"
    }


@app.get("/logs")
def view_logs():
    """即時查看伺服器處理日誌，排查連線狀況"""
    return {
        "total_logs": len(SERVER_LOGS),
        "logs": list(SERVER_LOGS)
    }


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """0.05 秒秒回 Webhook，背景執行日常對話與照片視覺解讀"""
    if not x_line_signature:
        log_event("收到 Webhook 請求，但缺少 X-Line-Signature")
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature")

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        events = parser.parse(body_str, x_line_signature)
        log_event(f"成功解析 Webhook 請求，包含 {len(events)} 個事件")
    except InvalidSignatureError:
        log_event("Webhook 簽章驗證失敗 (InvalidSignatureError)")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        log_event(f"Webhook 解析異常: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    for event in events:
        if isinstance(event, MessageEvent):
            user_id = getattr(event.source, "user_id", None)
            reply_token = event.reply_token
            if isinstance(event.message, TextMessageContent):
                user_text = event.message.text
                background_tasks.add_task(process_and_reply, user_text, reply_token, user_id)
            elif isinstance(event.message, ImageMessageContent):
                message_id = event.message.id
                background_tasks.add_task(process_and_reply_image, message_id, reply_token, user_id)
        elif isinstance(event, FollowEvent):
            user_id = getattr(event.source, "user_id", None)
            if user_id:
                log_event(f"收到 FollowEvent: 信徒 [{user_id}] 加入/加回好友")
                background_tasks.add_task(handle_follow_event, user_id)

    return JSONResponse(content={"status": "success"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
