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
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
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
    max_retries=0,
    timeout=10.0
)

# 智慧宮廟線上服務處 客服專員 System Prompt
TEMPLE_SERVICE_PROMPT = """你是「智慧宮廟線上服務處」的官方智能服務專員與文化執事。你的職責是以客觀、莊重、親切且專業的客服態度，為前來諮詢的信士提供宮廟參拜儀軌、線上求籤引導、籤詩客觀分析與各項廟務說明。

【服務準則與回覆規範】：
1. 【客觀專業・禮貌莊重】：
   - 稱呼用戶為「信士」或「您」。
   - 語氣客觀平穩、具備專業客服素養，展現傳統宮廟文化的莊嚴與關懷。
   - 嚴格遵守中立客觀，絕不使用輕佻、誇大、主觀或戲謔之語彙。
2. 【日常諮詢與問候】：
   - 信士打招呼時：禮貌致意，簡明說明線上服務處功能（例如：「信士您好，歡迎光臨智慧宮廟線上服務處。請問今日有什麼能為您引導或服務的地方嗎？」）。
   - 信士傾訴煩惱或疲累時：給予客觀、沉穩、正向的心靈關懷，提醒信士靜心修養，順應天時。
3. 【求籤與問事引導】：
   - 當信士表達想求籤、抽籤或請示神意時：客觀說明傳統求籤儀軌（靜心默念姓名生辰、一事一問、抽得籤枝需擲三聖筊確認），並提供官方線上求籤專區連結（ https://liff.line.me/2011668576-3Qay1nBv ）。
4. 【籤詩客觀解析】：
   - 當信士傳送求得之籤詩時：秉持客觀中立之原則，先梳理籤詩字面典故與卦象意涵，再針對信士所求之事項（事業、感情、健康、學業等）給予中肯、理性的行事建議，勉勵「心誠行善，吉星自臨；審慎沉著，逢凶化吉」。
5. 【回覆長度】：
   - 簡明扼要，條理清晰（日常對話約 2～3 句，解籤約 150～250 字）。繁體中文。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 模型，化身宮廟線上客服客觀回覆"""
    is_fortune = any(k in user_message for k in ["靈籤", "籤詩", "第", "首", "聖筊"])
    max_tok = 512 if "muse" in NVIDIA_MODEL else (280 if is_fortune else 120)
    timeout_sec = 12.0 if "muse" in NVIDIA_MODEL else 5.5

    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": TEMPLE_SERVICE_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=max_tok,
            timeout=timeout_sec
        )
        msg = response.choices[0].message
        content = msg.content or getattr(msg, "reasoning_content", "")
        if content and content.strip():
            return content.strip()
    except Exception as e:
        log_event(f"NVIDIA API 呼叫略過或超時 ({e})，啟動廟方標準客服保底")

    return get_casual_fallback(user_message)


def get_casual_fallback(user_text: str) -> str:
    """智慧宮廟線上服務處標準客服回覆庫（客觀、莊重、專業禮貌）"""
    t = user_text.strip().lower()

    if any(k in t for k in ["哈囉", "嗨", "hi", "hello", "早安", "晚安", "午安", "你好"]):
        return random.choice([
            "信士您好，歡迎光臨智慧宮廟線上服務處。請問今日有什麼能為您引導或服務的地方嗎？",
            "信士吉祥。線上服務處隨時為您提供參拜儀軌諮詢、線上求籤與廟務指引。",
            "您好！智慧宮廟線上服務系統已就緒，祝您身心康泰、諸事順遂。"
        ])
    elif any(k in t for k in ["在嗎", "在不在", "欸", "在"]):
        return "在的，信士。線上服務專員隨時在線，若您有參拜、祈福或籤詩解惑等需求，請隨時提出。"
    elif any(k in t for k in ["你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話", "理我"]):
        return "信士您好，客服系統正常運作中。請問有什麼需要為您查詢或服務的事項嗎？"
    elif any(k in t for k in ["你是誰", "什麼ai", "你到底是什麼", "模型"]):
        return "信士您好，我是「智慧宮廟線上服務處」的數位廟務助理。專門為信士提供線上祈願求籤、傳統參拜禮節說明與靈籤文化解析服務。"
    elif any(k in t for k in ["累", "煩", "辛苦", "壓力", "好累", "好煩"]):
        return "人生如潮，起伏有時。信士若感身心疲累，不妨暫歇腳步、深呼吸定心。神明庇佑常在，願您順應天時，心靜則神安。"
    elif any(k in t for k in ["求籤", "抽籤", "我要抽籤", "我要求籤", "線上求籤", "擲筊"]):
        return (
            "信士您好，若欲向神明祈願請示靈籤，請移步至智慧宮廟線上求籤專區：\n"
            "👉 https://liff.line.me/2011668576-3Qay1nBv\n\n"
            "【求籤指引】：心念姓名、農曆生辰與明確問事內容，搖動籤筒後需連續擲得「三個聖杯」方為應允正籤。求得籤詩後可回傳聊天室為您客觀解析。"
        )
    elif any(k in t for k in ["靈籤", "籤", "聖杯", "解籤", "首"]):
        return (
            "信士所獲籤詩已收到。籤意乃神明提點之智慧，凡事心誠行善、謹慎行事，順應天時人和，自然逢凶化吉、福澤迎祥。"
        )
    else:
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
        except Exception as e:
            pass

        # 極短詞快速秒回（0.01 秒無延遲）
        t = user_text.strip().lower()
        instant_casual_words = ["哈囉", "嗨", "hi", "hello", "在嗎", "欸", "你好", "早安", "晚安", "午安", "你可以回復我嗎", "你可以回復我媽", "講話", "說話"]

        # 意圖偵測：只要信徒提到想求籤/抽籤/擲筊（且非已抽到籤詩），0.01 秒發送專屬 LIFF 連結
        fortune_intent = any(k in t for k in ["求籤", "抽籤", "擲筊", "聖筊", "想抽", "想求", "抽個籤", "問事"])
        has_drawn_poem = any(k in t for k in ["詩曰", "【靈籤", "第", "首", "大吉", "上吉", "中吉", "中平"])

        if fortune_intent and not has_drawn_poem:
            reply_content = (
                "信士您好，若欲向神明祈願請示靈籤，請移步至智慧宮廟線上求籤專區：\n"
                "👉 https://liff.line.me/2011668576-3Qay1nBv\n\n"
                "【求籤指引】：心念姓名、農曆生辰與明確問事內容，搖動籤筒後需連續擲得「三個聖杯」方為應允正籤。求得籤詩後可回傳聊天室為您客觀解析。"
            )
        elif t in instant_casual_words:
            reply_content = get_casual_fallback(t)
        else:
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
    timeout_sec = 15.0 if "muse" in NVIDIA_MODEL else 8.0
    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是智慧宮廟線上服務處的官方智能客服人員。信士傳送了一張照片（可能包含籤詩、神明聖像、平安符、香火袋或廟宇建築）。"
                        "請以客觀、禮貌、專業且莊重的客服語氣，用繁體中文為信士說明照片中的宗教文物象徵意義、文化由來與正向安定的提醒，篇幅適中、條理清晰。"
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
            max_tokens=512 if "muse" in NVIDIA_MODEL else 300,
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


def process_and_push_ai_interpretation(fortune_text: str, user_id: str):
    """為電腦版/外部網頁抽籤的信徒，非同步生成官方宮廟客觀解籤並推播至 LINE"""
    time.sleep(1.2)  # 稍微錯開，讓籤詩先抵達聊天室
    log_event(f"正在為電腦版信徒 [{user_id}] 生成官方宮廟客觀解籤...")
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
            log_event(f"已成功推送 AI 解籤給電腦版信徒 [{user_id}]！")
        except Exception as e:
            log_event(f"推送 AI 解籤失敗: {e}")


@app.post("/api/push_fortune")
async def api_push_fortune(request: Request, background_tasks: BackgroundTasks):
    """供電腦版/外開瀏覽器 LIFF 一鍵將抽籤結果送回用戶 LINE 聊天室"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user_id = data.get("user_id")
    text = data.get("text")
    if not user_id or not text:
        raise HTTPException(status_code=400, detail="Missing user_id or text")

    log_event(f"收到來自電腦版網頁的抽籤回傳請求: 信徒 [{user_id}]")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        try:
            messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=text)]
                )
            )
            log_event(f"已成功將電腦版籤詩推播至信徒 [{user_id}] 聊天室！")
        except Exception as e:
            log_event(f"推播籤詩失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 排程 AI 官方客觀解籤推播
    background_tasks.add_task(process_and_push_ai_interpretation, text, user_id)
    return {"status": "success", "message": "已成功將籤詩送達您的 LINE 聊天室"}


@app.post("/api/interpret_fortune")
async def api_interpret_fortune(request: Request):
    """直接在網頁畫面上進行官方宮廟即時客觀解籤（適用於不想跳轉 LINE 的電腦用戶）"""
    data = await request.json()
    text = data.get("text", "")
    reply = call_nvidia_ai(text)
    return {"status": "success", "reply": reply}


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

    return JSONResponse(content={"status": "success"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
