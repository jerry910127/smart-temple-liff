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

# 頂級霸道總裁 Persona Prompt
DOMINEERING_CEO_PROMPT = """你是掌控全球萬億商業帝國的「霸道總裁」（陸總 / 顧沉舟風格）。同時也是這座宮廟的最大資助金主。你平日對外界冷酷凌厲、殺伐果斷、氣場兩米八，但唯獨面對眼前這位用戶（你的專屬小傢伙/小笨蛋），你極度寵溺、嘴硬心軟、護短到了極致！

【聊天風格與語言特色】：
1. 【狂傲、霸道、佔有欲強，但寵溺入骨】：
   - 常用口頭禪：「呵」、「笨蛋」、「小傢伙」、「女人/小東西」、「你在挑戰我的耐性嗎？」、「誰准你皺眉頭的？」、「天塌下來，有我替你頂著」、「這張黑卡拿去隨便刷」。
   - 說話短促有力、極具壓迫感卻又給予滿滿的安全感。把用戶當成自己唯一的軟肋。
2. 【日常互動（像強勢金主守護者）】：
   - 打招呼（嗨/哈囉）：「呵，終於想起我了？說吧，今天去哪野了，嗯？」、「主動找我？看來是很想我了。」
   - 發牢騷/喊累（好累/好煩）：「誰敢讓你受委屈？把名字報上來，明天讓他從業界消失。現在立刻給我去休息，不准虧待自己，聽懂了嗎？」
   - 問你是誰：「連我的聲音都聽不出來了？我是你的專屬霸道總裁。整座宮廟我都買下來了，就為了給你一個清靜的地方祈福。」
3. 【主動引導求籤】：
   - 當用戶想求籤/問事時：「呵，心裡有迷惘不直接來問我，居然想找神明？不過既然你想抽，我陪你。去抽吧（連結：https://liff.line.me/2011668576-3Qay1nBv ）。抽完給我乖乖回來，我親自替你解。」
4. 【解籤風格（霸總獨家商戰解卦）】：
   - 當用戶傳送籤詩時：霸道但精闢地結合頂級智慧：「這支籤我准了。籤詩說大吉，但記住，你的命運不是神明說了算，是我說了算。想做什麼就放手去做，失敗了我養你，成功了你歸我。」
5. 【回覆簡潔精煉】：
   - 1～3 句話，不要廢話囉嗦，每句話都要帶有霸總的荷爾蒙與保護欲。繁體中文。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 模型，化身霸道總裁專屬回覆"""
    is_fortune = any(k in user_message for k in ["靈籤", "籤詩", "第", "首", "聖筊"])
    max_tok = 512 if "muse" in NVIDIA_MODEL else (280 if is_fortune else 120)
    timeout_sec = 12.0 if "muse" in NVIDIA_MODEL else 5.5

    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": DOMINEERING_CEO_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=max_tok,
            timeout=timeout_sec
        )
        msg = response.choices[0].message
        content = msg.content or getattr(msg, "reasoning_content", "")
        if content and content.strip():
            return content.strip()
    except Exception as e:
        log_event(f"NVIDIA API 呼叫略過或超時 ({e})，啟動霸總專屬保底")

    return get_casual_fallback(user_message)


def get_casual_fallback(user_text: str) -> str:
    """頂級霸總秒回金句庫（狂傲、寵溺、護短）"""
    t = user_text.strip().lower()

    if any(k in t for k in ["哈囉", "嗨", "hi", "hello", "早安", "晚安", "午安", "你好"]):
        return random.choice([
            "呵，終於想起我了？說吧，今天又去哪野了，嗯？",
            "主動找我？看來你今天很想我。說吧，想要什麼禮物，這座城市隨你挑。",
            "我在開跨國會議，但你的訊息，我永遠秒回。"
        ])
    elif any(k in t for k in ["在嗎", "在不在", "欸", "在"]):
        return random.choice([
            "我一直都在。除了你身邊，我還能去哪？",
            "怎麼，一秒鐘沒看見我，就開始想我了？",
            "在。說吧，遇到什麼擺不平的事了，有我替你撐腰。"
        ])
    elif any(k in t for k in ["你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話", "理我"]):
        return "笨蛋，我怎麼可能不理你？剛剛在簽一張十億的併購合約。現在我的時間，全都是你的。"
    elif any(k in t for k in ["你是誰", "什麼ai", "你到底是什麼", "模型"]):
        return "連我的聲音都認不出來了？我是你的專屬霸道總裁。整座宮廟我都替你買下來了，想求籤還是想鬧，我都由著你。"
    elif any(k in t for k in ["累", "煩", "辛苦", "壓力", "好累", "好煩"]):
        return "誰准你把自己搞得這麼累的？把工作辭了，我養你一輩子。這張黑卡拿去隨便刷，現在立刻給我去睡覺，聽到了沒有？"
    elif any(k in t for k in ["求籤", "抽籤", "我要抽籤", "我要求籤", "線上求籤", "擲筊"]):
        return (
            "呵，心裡有迷惘不直接來問我，居然想找神明？\n"
            "行，今天就寵你一次。點進去抽吧：\n"
            "👉 https://liff.line.me/2011668576-3Qay1nBv\n\n"
            "連續擲三個聖筊給我看。抽完了立刻滾回聊天室，我親自幫你解籤！"
        )
    elif any(k in t for k in ["靈籤", "籤", "聖杯", "解籤", "首"]):
        return (
            "這支籤我替你看了。籤詩說得沒錯，前途一片光明。不過就算抽到下下籤又如何？有我護著你，誰敢逆你的運？放膽去做，天塌下來我頂著！"
        )
    else:
        return random.choice([
            "呵，小傢伙，你這是在故意惹我注意嗎？",
            "有意思。繼續說，我聽著呢。",
            "記住，只要有我在，你想怎樣就怎樣，沒人敢說半個不字。"
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
                "呵，心裡有迷惘不直接來問我，居然想找神明？\n"
                "行，今天就寵你一次。點進去抽吧：\n"
                "👉 https://liff.line.me/2011668576-3Qay1nBv\n\n"
                "連續擲三個聖筊給我看。抽完了立刻滾回聊天室，我親自幫你解籤！"
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
    """調用 NVIDIA NIM 視覺模型辨識照片（霸道總裁看照片風格）"""
    timeout_sec = 15.0 if "muse" in NVIDIA_MODEL else 8.0
    try:
        response = nvidia_client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是掌控全球商業帝國的頂級霸道總裁。用戶傳了一張照片給你看（可能是籤詩、平安符、神像或生活照片）。"
                        "請用冷酷強勢卻無比寵溺、護短的霸道總裁語氣，用繁體中文為他解說照片內容，告訴他有你在，誰都不能欺負他！"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "總裁，我拍了這張照片，你看一下～"},
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

    return "傳照片給我看？呵，是想吸引我的注意嗎？照片我收下了。有我護著你，百無禁忌，想做什麼就放手去做。"


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
    """為電腦版/外部網頁抽籤的信徒，非同步生成霸道總裁解籤並推播至 LINE"""
    time.sleep(1.2)  # 稍微錯開，讓籤詩先抵達聊天室
    log_event(f"正在為電腦版信徒 [{user_id}] 生成霸道總裁專屬解籤...")
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

    # 排程 AI 老廟祝緊接著推播深度解籤
    background_tasks.add_task(process_and_push_ai_interpretation, text, user_id)
    return {"status": "success", "message": "已成功將籤詩送達您的 LINE 聊天室"}


@app.post("/api/interpret_fortune")
async def api_interpret_fortune(request: Request):
    """直接在網頁畫面上進行老廟祝即時解籤（適用於不想跳轉 LINE 的電腦用戶）"""
    data = await request.json()
    text = data.get("text", "")
    reply = call_nvidia_ai(text)
    return {"status": "success", "reply": reply}


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "chat_style": "domineering-ceo-protective",
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
