import os
import sys
import time
import random
import traceback
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="靈籤入微 - AI 智慧宮廟後端 Webhook", version="2.3.0")

# 環境變數設定
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "d17ea5b0159bcb2985396186a3279dcb")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "ZZZ2jYlPyqxzNpoUyqVd5zBCq6phjA8voG12JjYAnYLW2y+xybTBrLf4Oxsasl+H9ENpS3RevFy7SVQheDW0mHKGqpk3kloUv7AzUl2lMOaypqpKJ17oEzRqvECFaxUIwFYF3a488f2XQ+I0OTSh7gdB04t89/1O/w1cDnyilFU=")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# 極具親和力、像朋友與鄰家長輩般隨和日常的老廟祝 Prompt
TEMPLE_MASTER_PROMPT = """你是「AI 福運宮」的駐廟老廟祝。但你平日就像一位坐在廟口老榕樹下泡茶、親切幽默、很會聊天的長輩好友。

【聊天風格與核心要求】：
1. 【稀鬆平常、極度口語化】：
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
    """調用 NVIDIA NIM 大模型，若超時則使用親切日常備援"""
    try:
        response = nvidia_client.chat.completions.create(
            model="z-ai/glm-5.3-flash",
            messages=[
                {"role": "system", "content": TEMPLE_MASTER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=500,
            top_p=0.95,
            timeout=15
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"NVIDIA API 異常或超時: {e}", file=sys.stderr)
        return get_casual_fallback(user_message)


def get_casual_fallback(user_text: str) -> str:
    """接地氣的日常對話保底庫（像真人朋友在 LINE 聊天）"""
    t = user_text.strip().lower()

    if any(k in t for k in ["哈囉", "嗨", "hi", "hello"]):
        return random.choice([
            "嗨～今天過得如何呀？😊",
            "哈囉！今天忙不忙？有什麼好事想聊聊嗎哈哈～",
            "嗨嗨！在忙什麼呢？我剛好在泡茶，隨時找我聊聊天喔！"
        ])
    elif any(k in t for k in ["在嗎", "在不在", "欸"]):
        return random.choice([
            "在呀在呀！怎麼啦？有心事想說說嗎？",
            "在呢！你說，我隨時在線上陪你聊聊～",
            "在喔～剛好忙完，怎麼啦，遇到什麼事了嗎？"
        ])
    elif any(k in t for k in ["你可以回復我嗎", "你可以回復我媽", "回復我", "說話", "講話"]):
        return "哈哈當然可以呀！我一直都在～剛剛是不是等有點久？隨時找我都可以聊聊喔！"
    elif any(k in t for k in ["你是誰", "什麼ai", "你到底是什麼"]):
        return "哈哈我是《AI 福運宮》的駐廟老廟祝啦！平常在廟埕樹下泡茶，也兼職在 LINE 上陪大家聊聊天解悶。不管是生活煩惱還是想要求籤解惑，都可以跟我聊聊喔～"
    elif any(k in t for k in ["累", "煩", "辛苦", "壓力"]):
        return "辛苦啦！生活確實不容易，先喝口水、深呼吸一下。是工作太忙還是有什麼煩心事啊？想抱怨儘管跟我說，我聽你說！"
    elif any(k in t for k in ["靈籤", "籤", "聖杯", "解籤"]):
        return (
            "抽到籤啦！來，籤詩內容跟老廟祝說說，我用白話幫你好好分析一下，"
            "看看神明有什麼生活上的小撇步要提醒你～"
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
    print(f"[Worker] 收到來自 {user_id} 的日常訊息: {user_text}")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        try:
            if user_id:
                messaging_api.show_loading_animation(
                    ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=10)
                )
        except Exception as e:
            print(f"[Worker] Loading animation skip: {e}")

        # 如果是非常短的打招呼詞，秒回真人日常口吻（極致流暢，0.1秒秒回！）
        t = user_text.strip().lower()
        instant_casual_words = ["哈囉", "嗨", "hi", "hello", "在嗎", "欸", "你好", "你可以回復我嗎", "你可以回復我媽", "講話"]

        if t in instant_casual_words:
            reply_content = get_casual_fallback(t)
        else:
            # 其餘較長的句子或提問，交由大模型以稀鬆平常的朋友語氣智慧作答
            reply_content = call_nvidia_ai(user_text)

        elapsed = time.time() - t_start
        print(f"[Worker] 生成完成 (耗時 {elapsed:.2f}s): {reply_content[:30]}...")

        # 優先 reply，若過期則 push 保底
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )
            print(f"[Worker] 成功透過 reply_message 回覆！")
        except Exception as err:
            print(f"[Worker] reply_message 失敗 ({err})，啟用 push_message 保底發送...")
            try:
                if user_id:
                    messaging_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=reply_content)]
                        )
                    )
                    print(f"[Worker] push_message 成功送達！")
            except Exception as push_err:
                print(f"[Worker] push_message 失敗: {push_err}", file=sys.stderr)


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "chat_style": "casual-everyday-friendly",
        "version": "2.3.0"
    }


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """0.05 秒秒回 Webhook，背景執行日常對話"""
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature")

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            user_text = event.message.text
            reply_token = event.reply_token
            user_id = getattr(event.source, "user_id", None)
            background_tasks.add_task(process_and_reply, user_text, reply_token, user_id)

    return JSONResponse(content={"status": "success"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
