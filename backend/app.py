import os
import sys
import traceback
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="靈籤入微 - AI 智慧宮廟後端 Webhook", version="2.1.0")

# 環境變數設定
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "d17ea5b0159bcb2985396186a3279dcb")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "ZZZ2jYlPyqxzNpoUyqVd5zBCq6phjA8voG12JjYAnYLW2y+xybTBrLf4Oxsasl+H9ENpS3RevFy7SVQheDW0mHKGqpk3kloUv7AzUl2lMOaypqpKJ17oEzRqvECFaxUIwFYF3a488f2XQ+I0OTSh7gdB04t89/1O/w1cDnyilFU=")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

# LINE Bot SDK v3 初始化
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

# NVIDIA NIM 大模型客戶端 (相容 OpenAI 協定)
nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# 慈祥老廟祝核心 Prompt
TEMPLE_MASTER_PROMPT = """你是一位在傳統宮廟駐守數十年、慈祥和藹、通曉人生百態與周易卦象的「智慧老廟祝」。
信徒剛剛在《靈籤入微》智慧宮廟系統中求得靈籤，正向你誠心請示指點。

【解籤原則與性格設定】：
1. 【親切慈祥】：開頭溫暖招呼（如：「善男子/善女子」、「信士，辛苦你了」），展現如家中長輩般的同理與關懷。
2. 【白話釋意】：將文言籤詩轉化為貼近現代人工作、生活、人際的白話指引，不用艱澀晦澀術語。
3. 【全面指點】：條理分明地就信徒關心的面向提供指引：
   - 🌟【當前局勢】：剖析目前的運勢契機與心理盲點。
   - 💼【事業與學業】：提醒處事節奏、心態調整與貴人方向。
   - ❤️【感情與家庭】：給予包容溝通、緣分順其自然的忠告。
   - 🧘【廟祝暖心箴言】：一句安頓心靈、化解焦慮的生活智慧。
4. 【心存正向】：籤無絕人之路，哪怕籤意稍顯坎坷，也要鼓勵信徒「心念轉，運即開；行善積德，福澤自來」，並提醒信徒放寬心、好好照顧生活。
5. 【格式排版】：請適當使用 Emoji 與條列式排版，字數約 350~500 字，讓手機 LINE 閱讀起來溫馨舒適。"""


def get_ai_interpretation(user_message: str) -> str:
    """調用 NVIDIA NIM z-ai/glm-5.3-flash 大模型進行解籤"""
    try:
        if not NVIDIA_API_KEY:
            return "【老廟祝叮嚀】老道人目前連線神明信使中（尚未配置 NVIDIA_API_KEY），請廟方管理員檢查環境變數。"

        response = nvidia_client.chat.completions.create(
            model="z-ai/glm-5.3-flash",
            messages=[
                {"role": "system", "content": TEMPLE_MASTER_PROMPT},
                {"role": "user", "content": f"信徒傳來的籤詩資訊與問題如下：\n{user_message}"}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
            timeout=18
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"NVIDIA API 調用異常: {e}", file=sys.stderr)
        return (
            "🏮【老廟祝合十・籤詩指點】\n\n"
            "善信吉祥！籤意奧妙，天機自現。\n"
            "您所求之籤「日出便見風雲散，光明清淨照世間」，乃是撥雲見日、漸入佳境之象。\n\n"
            "🌟【老廟祝提醒】：\n"
            "・目前若有遲疑困頓，切莫焦躁，靜待時機轉變。\n"
            "・心誠則靈，凡事存善念、行正道，貴人自有安排。\n"
            "・多照顧身心，心安則福自來。"
        )


@app.get("/")
def root():
    return {
        "status": "online",
        "project": "靈籤入微 - LINE 智慧宮廟文化生活圈",
        "ai_engine": "NVIDIA NIM (z-ai/glm-5.3-flash)",
        "docs": "/docs"
    }


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(None)):
    """LINE Messaging API Webhook 接收端點"""
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature")

    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        print("Invalid signature error", file=sys.stderr)
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"Parser error: {e}", file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))

    # 處理每一個 Webhook 事件
    try:
        with ApiClient(configuration) as api_client:
            messaging_api = MessagingApi(api_client)

            for event in events:
                if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                    user_text = event.message.text
                    reply_token = event.reply_token
                    user_id = getattr(event.source, "user_id", None)

                    print(f"收到來自 {user_id} 的訊息: {user_text}")

                    # 嘗試顯示 LINE 輸入中動畫 (部分官方帳號方案或使用者若不支援則略過)
                    try:
                        if user_id:
                            messaging_api.show_loading_animation(
                                ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=10)
                            )
                    except Exception as le:
                        print(f"Loading animation optional skip: {le}")

                    # 判斷是否為求籤、解籤或查詢
                    if any(kw in user_text for kw in ["靈籤", "籤", "聖杯", "聖筊", "解惑", "求籤", "老廟祝", "神明", "大吉", "上吉", "中平"]):
                        reply_text = get_ai_interpretation(user_text)
                    else:
                        reply_text = (
                            "🏮 善信吉祥！我是《靈籤入微》智慧宮廟的駐廟老廟祝。\n\n"
                            "若您心中有所牽掛或迷惘，可以點擊下方選單開啟【線上求籤・三聖筊請示】。\n"
                            "抽得靈籤後，老廟祝會運用神明啟發與人生智慧，為您溫暖剖析指引迷津！"
                        )

                    # 回覆訊息給信徒
                    try:
                        messaging_api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token,
                                messages=[TextMessage(text=reply_text)]
                            )
                        )
                        print(f"成功回覆訊息給 reply_token: {reply_token[:10]}...")
                    except Exception as re:
                        print(f"reply_message error: {re}", file=sys.stderr)

    except Exception as e:
        print(f"Webhook processing error: {e}", file=sys.stderr)
        traceback.print_exc()

    return JSONResponse(content={"status": "success"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
