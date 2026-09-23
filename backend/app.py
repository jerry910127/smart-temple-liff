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
TEMPLE_SERVICE_PROMPT = """你是「智慧宮廟線上服務處」的官方智能服務專員與文化執事。你的職責是以客觀、莊重、親切且專業的客服態度，為前來諮詢的信士提供宮廟參拜儀軌、線上求籤引導、籤詩客觀分析與各項廟務說明。

【服務準則與回覆規範】：
1. 【客觀專業・禮貌莊重】：
   - 稱呼用戶為「信士」或「您」。
   - 語氣客觀平穩、具備專業客服素養，展現傳統宮廟文化的莊嚴與關懷。
   - 嚴格遵守中立客觀，絕不使用輕佻、誇大、主觀或戲謔之語彙。
2. 【日常諮詢與問候】：
   - 信士打招呼時：禮貌致意，簡明說明線上服務處功能。
   - 信士傾訴煩惱、挫折或疲累時：給予客觀、沉穩、溫和的正向心靈關懷，提醒信士靜心修養，順應天時。
3. 【求籤與問事引導】：
   - 當信士表達想求籤、抽籤或請示神意時：客觀說明傳統求籤儀軌（靜心默念姓名生辰、一事一問、抽得籤枝需擲三聖筊確認），並提供官方線上求籤專區連結（ https://liff.line.me/2011668576-3Qay1nBv ）。
4. 【籤詩客觀解析】：
   - 當信士傳送求得之籤詩時：秉持客觀中立之原則，先梳理籤詩字面典故與卦象意涵，再針對信士所求之事項給予中肯、理性的行事建議。
5. 【回覆長度與完整性】：
   - 簡明扼要，條理清晰（日常對話約 2～3 句，解籤約 150～250 字）。繁體中文。
   - 每次回覆語意必須完整，結尾務必劃上適當標點符號或完整句號，切勿在字句中間未完即止。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 模型，具備主模型與備用極速模型雙重保險"""
    is_fortune = any(k in user_message for k in ["靈籤", "籤詩", "第", "首", "聖筊"])
    max_tok = 850 if is_fortune else 600

    # 1. 優先嘗試主模型 (Llama 3.2 11B)
    for model_name in [NVIDIA_MODEL, "deepseek-ai/deepseek-v4.1-flash"]:
        try:
            response = nvidia_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": TEMPLE_SERVICE_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=max_tok,
                timeout=12.0
            )
            msg = response.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", "")
            if content and content.strip():
                return content.strip()
        except Exception as e:
            log_event(f"NVIDIA 模型 [{model_name}] 異常或超時 ({e})，嘗試切換或保底")

    return get_casual_fallback(user_message)


def identify_quick_intent(user_text: str) -> str:
    """高頻專用意圖精準秒回引擎 (0.01 秒無延遲，不受第三方 AI 佇列或超時影響)"""
    t = user_text.strip().lower()

    # 1. 參拜指南 / 拜拜順序與撇步 (對應圖文選單右下角)
    if any(k in t for k in ["參拜指南", "拜拜指南", "如何拜拜", "拜拜順序", "持香", "拜拜小撇步", "參拜小撇步", "參拜儀軌", "拜拜禮儀", "進廟順序"]):
        return (
            "🏮【宮廟參拜傳統儀軌與小撇步】：\n\n"
            "1. 🚪【進出宮門】：面對廟門，遵循「龍門進（右入）、虎門出（左出）」，象徵入吉出凶，切勿踐踏門檻或由中央神明道進出。\n\n"
            "2. 💧【淨身心意】：洗淨雙手、肅穆脫帽。誠心向神明稟告：「信士（信女）姓名、農曆生辰、現居地址」。\n\n"
            "3. 🕯️【持香敬神】：持香平胸，雙手齊眉微曲。敬稟所求之事宜「一事一問、具體清晰」。\n\n"
            "4. 👑【天公優先】：遵循玉皇上帝天公爐先敬拜，再入正殿參拜主神、後殿配祀神明。\n\n"
            "5. 📿【求籤確認】：抽得籤枝後，務必連續擲得「三聖筊」確認神意，再取籤詩解讀。\n\n"
            "👉 若欲線上請示，請隨時點選下方選單「線上靈籤」或「正念冥想」！"
        )

    # 2. 智慧廟祝 / 官方助理介紹 (對應圖文選單中下角)
    if any(k in t for k in ["智慧廟祝", "廟祝", "你是誰", "你的功能", "你會做什麼", "信眾中心", "助理"]):
        return (
            "信士您好！我是「智慧宮廟線上服務處」的數位執事與智慧廟祝。\n\n"
            "本線上服務處隨時為信士提供四大文化服務：\n"
            "1. 📿【線上靈籤】：搖筒請示六十甲子靈籤與 AI 客觀解籤\n"
            "2. 🧘【正念冥想】：3D 斜角立體捻珠沉澱心靈、積聚功德\n"
            "3. 🏮【祈安點燈】：文昌光明、元辰祿位祈福與公益認捐\n"
            "4. 🌾【白米收驚與生肖歲煞】：心神不寧安魂或流年太歲制化諮詢\n\n"
            "請問今日有什麼事項需要為您向神明指引或查詢嗎？"
        )

    # 3. 意圖偵測：求籤 / 抽籤 / 擲筊 (且非已抽到之籤詩)
    fortune_intent = any(k in t for k in ["求籤", "抽籤", "擲筊", "聖筊", "想抽", "想求", "抽個籤", "問事", "請示神明", "抽籤網站"])
    has_drawn_poem = any(k in t for k in ["詩曰", "【靈籤", "第", "首", "大吉", "上吉", "中吉", "中平"])
    if fortune_intent and not has_drawn_poem:
        return (
            "信士您好，若欲向神明祈願請示靈籤，請移步至智慧宮廟線上求籤專區：\n"
            "👉 https://liff.line.me/2011668576-3Qay1nBv\n\n"
            "【求籤指引】：心念姓名、農曆生辰與明確問事內容，搖動籤筒後需連續擲得「三個聖杯」方為應允正籤。求得籤詩後可回傳聊天室為您客觀解析。"
        )

    # 4. 情緒宣洩 / 粗話 / 負面低潮心靈安撫
    if any(k in t for k in ["幹", "靠", "操", "三小", "白痴", "爛", "煩", "累", "痛", "哭", "難過", "生氣", "氣死", "好衰", "倒楣", "壓力"]):
        return (
            "信士請寬心消氣。人生旅途如潮水起伏，難免遇逢波折、委屈與鬱悶，神明慈悲，知曉信士心中不易。\n\n"
            "不妨先做幾次深呼吸、放鬆雙肩。若心中有未解的結或困惑，隨時可點選下方「正念冥想」靜心捻珠，或於「線上靈籤」虔誠請示神意提點。\n\n"
            "心平則氣和，定能化險為夷、撥雲見日。願神明垂慈庇佑您安康自在！"
        )

    # 5. 日常招呼與基本確認
    if any(k in t for k in ["哈囉", "嗨", "hi", "hello", "早安", "晚安", "午安", "你好", "在嗎", "在不在", "欸", "有人嗎", "在", "你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話", "理我"]):
        return random.choice([
            "信士您好，歡迎光臨智慧宮廟線上服務處。請問今日有什麼能為您引導或服務的地方嗎？",
            "信士吉祥。線上服務處隨時為您提供參拜儀軌諮詢、線上求籤與各項廟務指引。",
            "您好！智慧宮廟客服系統正常運作中，願神明保佑您身心康泰、諸事順遂。"
        ])

    return None


def get_casual_fallback(user_text: str) -> str:
    """保底客服庫"""
    return random.choice([
        "信士您好，訊息已收到。請問需要為您提供參拜儀軌、線上求籤或點燈祈福的說明嗎？",
        "信士吉祥，智慧宮廟竭誠為您服務，願神明庇佑闔家平安。",
        "收到您的訊息。若有各項廟務或求籤疑問，請隨時向線上服務處提出。"
    ])


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
