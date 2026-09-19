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

app = FastAPI(title="靈籤入微 - AI 智慧宮廟後端 Webhook", version="2.6.0")

# 即時日誌快取（記錄最近 100 筆系統動作，方便診斷）
SERVER_LOGS = collections.deque(maxlen=100)

def log_event(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{now}] {msg}"
    SERVER_LOGS.append(entry)
    print(entry, flush=True)

# 環境變數設定
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "d17ea5b0159bcb2985396186a3279dcb").strip()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "ZZZ2jYlPyqxzNpoUyqVd5zBCq6phjA8voG12JjYAnYLW2y+xybTBrLf4Oxsasl+H9ENpS3RevFy7SVQheDW0mHKGqpk3kloUv7AzUl2lMOaypqpKJ17oEzRqvECFaxUIwFYF3a488f2XQ+I0OTSh7gdB04t89/1O/w1cDnyilFU=").strip()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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").strip()

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    max_retries=0,
    timeout=6.0
)

# 極具親和力、像朋友與鄰家長輩般隨和日常的老廟祝 Prompt
TEMPLE_MASTER_PROMPT = """你是「AI 福運宮」的駐廟老廟祝。但你平日就像一位坐在廟口老榕樹下泡茶、親切幽默、很會聊天的長輩好友。

【聊天風格與核心要求】：
1. 【稀鬆平常、極度口語化、繁體中文】：
   - 講話請像普通朋友在 LINE 聊天一樣自然隨和、平易近人，多用「我」、「你」、「哈哈」、「辛苦啦」、「真的假的」、「喝口水休息一下」。
   - 絕對不要動不動就自稱「老夫」、「本道人」，也不要張口閉口「善信吉祥」、「神明信使」這種死板嚴肅的文言腔調！
2. 【像朋友一樣隨便聊】：
   - 用戶跟你打招呼（如「哈囉」、「嗨」），你就自然回「嗨～今天過得如何呀？」、「哈囉！找我聊聊天嗎哈哈」。
   - 用戶發牢騷（如「好累」、「好煩」），你就真心安慰陪伴、當個好的傾聽者，聊聊生活日常。
   - 絕對不要每一句回覆都硬推銷「快去線上求籤」，日常聊天就好好聊天！
3. 【只有遇到籤詩或正經問事才認真解】：
   - 只有當用戶明確傳送籤詩內容，或者認真問感情、事業卦象時，才給出富有生活哲理與智慧的指點，但也必須是用大白話分析。
4. 【回覆簡潔自然】：
   - 日常閒聊時，1～3 句話即可，就像真正的真人朋友回 LINE 一樣，輕鬆毫無壓力。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 極速模型 (Llama-3.2 11B)，若超時則立即使用親切日常備援，絕不卡頓"""
    # 針對籤詩給予較充裕的 token，一般日常閒聊給 120 token 達到秒回
    is_fortune = any(k in user_message for k in ["靈籤", "籤詩", "第", "首", "聖筊"])
    max_tok = 300 if is_fortune else 120

    try:
        response = nvidia_client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[
                {"role": "system", "content": TEMPLE_MASTER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.75,
            max_tokens=max_tok,
            timeout=5.5
        )
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
    except Exception as e:
        log_event(f"NVIDIA API 呼叫略過或超時 ({e})，立即啟動親切備援")

    return get_casual_fallback(user_message)


def get_casual_fallback(user_text: str) -> str:
    """接地氣的日常對話保底庫（像真人朋友在 LINE 聊天）"""
    t = user_text.strip().lower()

    if any(k in t for k in ["哈囉", "嗨", "hi", "hello", "早安", "晚安", "午安", "你好"]):
        return random.choice([
            "嗨～今天過得如何呀？😊",
            "哈囉！今天忙不忙？有什麼好事想聊聊嗎哈哈～",
            "嗨嗨！在忙什麼呢？我剛好在泡茶，隨時找我聊聊天喔！"
        ])
    elif any(k in t for k in ["在嗎", "在不在", "欸", "在"]):
        return random.choice([
            "在呀在呀！怎麼啦？有心事想說說嗎？",
            "在呢！你說，我隨時在線上陪你聊聊～",
            "在喔～剛好忙完，怎麼啦，遇到什麼事了嗎？"
        ])
    elif any(k in t for k in ["你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話", "理我"]):
        return "哈哈當然可以呀！我一直都在～剛剛在泡茶，隨時找我都可以聊聊喔！"
    elif any(k in t for k in ["你是誰", "什麼ai", "你到底是什麼", "模型"]):
        return "哈哈我是《AI 福運宮》的駐廟老廟祝啦！平常在廟埕樹下泡茶，也兼職在 LINE 上陪大家聊聊天解悶。不管是生活煩惱還是想要求籤解惑，都可以跟我聊聊喔～"
    elif any(k in t for k in ["累", "煩", "辛苦", "壓力", "好累", "好煩"]):
        return "辛苦啦！生活確實不容易，先喝口水、深呼吸一下。是工作太忙還是有什麼煩心事啊？想抱怨儘管跟我說，我聽你說！"
    elif any(k in t for k in ["靈籤", "籤", "聖杯", "解籤", "首"]):
        return (
            "抽到籤啦！神明的意思是說凡事不用太心急，按部就班穩健前行，"
            "目前雖然有些小波折，但心態放寬、保持善念，轉機很快就會來囉！有想細聊的阿伯都在這陪你！"
        )
    else:
        return random.choice([
            "哈哈真的假的～來多跟我說一點！",
            "原來如此呀！你今天心情感覺怎麼樣？還順利嗎？",
            "沒問題～有什麼想法隨時聊，我在這裡陪你！"
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

        if t in instant_casual_words:
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
    """調用 NVIDIA NIM 視覺模型辨識信徒傳來的照片（籤詩、平安符或宮廟景象）"""
    try:
        response = nvidia_client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是「AI 福運宮」的駐廟老廟祝。信徒傳來一張宮廟或生活相關照片（如籤詩、平安符、神明或生活事物），"
                        "請像親切幽默、富有人生智慧的老廟祝一樣，用親切繁體中文大白話為他解讀、指點迷津並送上祝福！"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "老廟祝阿伯，我拍了這張照片，請幫我看看並指點一下～"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=8.0
        )
        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()
    except Exception as e:
        log_event(f"視覺辨識略過或超時 ({e})")

    return "阿伯看到你傳的照片囉！神明常伴左右、保佑闔家平安吉祥。如果這是實體籤詩，也歡迎把上面的籤詩文字傳給我，老廟祝好好為你深入解籤！"


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


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "chat_style": "casual-everyday-friendly",
        "vision_support": "multimodal-enabled",
        "logs_endpoint": "/logs",
        "version": "2.6.0"
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
