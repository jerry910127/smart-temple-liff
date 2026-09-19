import os
import sys
import time
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

app = FastAPI(title="靈籤入微 - AI 智慧宮廟後端 Webhook", version="2.2.0")

# 環境變數設定 (預設直接填入使用者憑證確保高可用)
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "d17ea5b0159bcb2985396186a3279dcb")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "ZZZ2jYlPyqxzNpoUyqVd5zBCq6phjA8voG12JjYAnYLW2y+xybTBrLf4Oxsasl+H9ENpS3RevFy7SVQheDW0mHKGqpk3kloUv7AzUl2lMOaypqpKJ17oEzRqvECFaxUIwFYF3a488f2XQ+I0OTSh7gdB04t89/1O/w1cDnyilFU=")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

TEMPLE_MASTER_PROMPT = """你是一位在傳統宮廟駐守數十年、慈祥和藹、通曉人生百態與周易卦象的「智慧老廟祝」。
你在《靈籤入微：LINE 智慧宮廟文化生活圈》中為信眾指點迷津。你的技術底座是由 NVIDIA NIM 平台大模型所驅動，說話風格充滿慈悲、溫暖、有智慧。

【回應原則】：
1. 【親切慈祥】：開頭溫暖招呼（如：「善信吉祥」、「信士，辛苦你了」），展現長輩般的同理與關懷。
2. 【情境自適應處理】：
   - 🎋【若信徒傳來籤詩或求籤結果】：
     條理分明進行深度解籤：
     * 🌟【當前運勢走勢】：點出契機與注意盲點。
     * 💼【事業與學業】：提醒處事節奏、心態調整與貴人方向。
     * ❤️【感情與人際】：給予包容溝通、順其自然的忠告。
     * 🧘【廟祝暖心箴言】：一句安頓心靈的生活智慧。
   - 💬【若信徒日常問候或問你是誰】（如「哈囉」、「你好」、「你是什麼AI」）：
     * 溫和親切地問好，介紹自己是《靈籤入微》的 AI 智慧老廟祝。
     * 結合傳統籤詩智慧與 AI 科技，傾聽心聲。邀請對方若有疑惑，可點開【線上求籤】搖籤請示！
3. 【心存正向】：鼓勵信徒「心念轉，運即開；行善積德，福澤自來」。排版適度使用 Emoji 與條列，字數約 200~350 字，舒適溫暖。"""


def call_nvidia_ai(user_message: str) -> str:
    """調用 NVIDIA NIM 大模型，帶超時與優雅備援"""
    try:
        response = nvidia_client.chat.completions.create(
            model="z-ai/glm-5.3-flash",
            messages=[
                {"role": "system", "content": TEMPLE_MASTER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=800,
            top_p=0.9,
            timeout=20
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"NVIDIA API 呼叫超時或異常: {e}", file=sys.stderr)
        # 若為日常問候的快速智慧備援
        if any(w in user_message for w in ["哈囉", "嗨", "你好", "在嗎", "你可以", "欸"]):
            return (
                "🏮 善信吉祥！老廟祝在呢。\n\n"
                "老夫剛才在正殿添油點燈，怠慢善信了。\n"
                "您近日心中是否有牽掛、猶豫不決的事？\n"
                "老廟祝在此傾聽，您也可以點擊下方選單開啟【線上求籤・三聖筊請示】，"
                "讓神明賜予靈籤指引迷津喔！"
            )
        elif any(w in user_message for w in ["你是誰", "什麼ai", "ai"]):
            return (
                "🏮 善信吉祥！我是《靈籤入微：智慧宮廟》的駐廟老廟祝。\n\n"
                "老夫背後由先進的 NVIDIA NIM 大模型驅動，結合數十年民間信仰的靈籤精粹與人生智慧，"
                "專門為在生活、事業、感情中感到迷惘的信眾解籤祈福、安頓心靈。\n\n"
                "若您有想請示的事情，歡迎隨時向神明求籤！"
            )
        else:
            return (
                "🏮【老廟祝合十・籤詩指點】\n\n"
                "善信吉祥！籤意奧妙，天機自現。\n"
                "「日出便見風雲散，光明清淨照世間」，此乃撥雲見日、漸入佳境之大吉象徵！\n\n"
                "🌟【老廟祝心法】：\n"
                "・目前若有遲疑困頓，切莫焦躁，靜待時機自然轉化。\n"
                "・心誠則靈，凡事存善念、行正道，自有貴人相助。\n"
                "・凡事心安，則福澤自來！"
            )


def process_and_reply(user_text: str, reply_token: str, user_id: str):
    """在背景非同步執行 AI 運算並透過 LINE 送出訊息，絕不阻斷 Webhook"""
    t_start = time.time()
    print(f"[Worker] 開始處理來自 {user_id} 的訊息: {user_text}")

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)

        # 嘗試顯示 LINE 輸入中動畫
        try:
            if user_id:
                messaging_api.show_loading_animation(
                    ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=15)
                )
        except Exception as e:
            print(f"[Worker] Loading animation notice: {e}")

        # 快速問候直接回覆（低於 0.1 秒秒回），其餘走大模型深度思考
        quick_greetings = ["哈囉", "嗨", "hi", "hello", "在嗎", "你好", "欸", "你可以回復我嗎", "你可以回復我媽", "講話"]
        cleaned_text = user_text.strip().lower()

        if cleaned_text in quick_greetings:
            reply_content = (
                "🏮 善信吉祥！老廟祝在呢，聽到您的呼喚了。\n\n"
                "您近日生活或工作上是否遇上了困惑、或是心中有所牽掛？\n"
                "老廟祝在此陪您聊聊，隨時為您指引方向。\n\n"
                "若想向神明請示特定事項，歡迎點開【線上求籤】搖動靈籤與擲筊！"
            )
        else:
            # 呼叫 NVIDIA NIM 大模型
            reply_content = call_nvidia_ai(user_text)

        elapsed = time.time() - t_start
        print(f"[Worker] 訊息生成完成 (耗時 {elapsed:.2f}s)，準備發送給信徒...")

        # 優先使用 reply_message，若 reply_token 失效則使用 push_message 保底！
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_content)]
                )
            )
            print(f"[Worker] 成功透過 reply_message 發送！")
        except Exception as err:
            print(f"[Worker] reply_message 失敗: {err}，啟用 push_message 保底發送...")
            try:
                if user_id:
                    messaging_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=reply_content)]
                        )
                    )
                    print(f"[Worker] 成功透過 push_message 發送給 {user_id}！")
            except Exception as push_err:
                print(f"[Worker] push_message 也失敗: {push_err}", file=sys.stderr)


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "ai_engine": "NVIDIA NIM (z-ai/glm-5.3-flash)",
        "mode": "async-background-worker",
        "version": "2.2.0"
    }


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """LINE Messaging API Webhook 接收端點：0.05 秒極速響應，非同步背景處理"""
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

            # 把繁重的 AI 運算交給 BackgroundTasks，主執行緒立即向 LINE 返回 200 OK
            background_tasks.add_task(process_and_reply, user_text, reply_token, user_id)

    # 立即返回 200 OK，LINE 伺服器永遠不會超時中斷！
    return JSONResponse(content={"status": "success"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
