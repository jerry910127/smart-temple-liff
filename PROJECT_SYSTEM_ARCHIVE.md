# ⛩️ LINE Bye・智慧宮廟文化生活圈 (Smart Temple LIFF / MINI App)
## 系統全架構、環境參數、LLM 設定與開發延續手冊

> **本檔案用途**：收錄專案所有前端網址、LINE Developers 參數、後端 Render 服務端點、NVIDIA NIM LLM 模型設定、官方宮廟客觀客服 Prompt、心理學擲筊動態機率公式、UI 座標與歷史除錯紀錄。方便日後切換 LLM 或交接延續開發時，一鍵查閱即可無縫接軌。
> **建立時間**：2026-09-20  
> **系統版本**：v3.2.0 (LINE Bye Portal + 廟方智能客服客觀版)

---

## 目錄
1. [專案網址與連線端點彙整](#一專案網址與連線端點彙整)
2. [LINE 平台金鑰與頻道參數](#二line-平台金鑰與頻道參數)
3. [後端 Render 伺服器與 API 端點](#三後端-render-伺服器與-api-端點)
4. [LLM 模型與官方宮廟客服 Prompt 完整設定](#四llm-模型與官方宮廟客服-prompt-完整設定)
5. [前端心理學博弈與成癮保底機制](#五前端心理學博弈與成癮保底機制)
6. [LINE Bye (LINE Pay / LINE GO 風格) UI 座標架構](#六line-bye-line-pay--line-go-風格-ui-座標架構)
7. [歷史除錯紀錄與關鍵架構設計 (FAQ)](#七歷史除錯紀錄與關鍵架構設計-faq)

---

## 一、專案網址與連線端點彙整

| 項目 | 網址 / 端點 | 說明 |
| :--- | :--- | :--- |
| **GitHub 專案庫** | `https://github.com/jerry910127/smart-temple-liff` | 專案主要代碼庫 (分支: `main` 與 `feat/temple-culture-v2`) |
| **GitHub Pages 正式網址** | `https://jerry910127.github.io/smart-temple-liff/` | 前端靜態網頁託管 (LINE MINI App 終端 Endpoint URL) |
| **LINE MINI App (Developing)** | `https://miniapp.line.me/2011672732-8VId10cb` | **目前測試使用**，LIFF ID: `2011672732-8VId10cb` |
| **LINE MINI App (Review)** | `https://miniapp.line.me/2011672733-59eN6KAB` | 送審階段專用，LIFF ID: `2011672733-59eN6KAB` |
| **LINE MINI App (Published)** | `https://miniapp.line.me/2011672734-RX4TBGQf` | 正式發布公開專用，LIFF ID: `2011672734-RX4TBGQf` |
| **舊版 LINE Login LIFF** | `https://liff.line.me/2011668576-3Qay1nBv` | 第一代 LIFF 測試連結，LIFF ID: `2011668576-3Qay1nBv` |
| **後端 Render 伺服器** | `https://smart-temple-liff.onrender.com` | FastAPI + Uvicorn 雲端伺服器 (Render Web Service) |
| **Google Maps Platform** | `Maps JavaScript API` | 前端真實宮廟地圖、客製化足跡 Marker、路線 Polyline 與導航 |

---

## 二、LINE 平台金鑰與頻道參數

在 `backend/.env` 或 Render 後台 Environment Variables 需設定：

```env
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
NVIDIA_API_KEY=your_nvidia_api_key_here
PORT=8000
```

* **LINE Developers Webhook URL**：`https://smart-temple-liff.onrender.com/webhook`（已開啟 Use webhook，且支援驗證）
* **LIFF Scopes 權限**：`profile`, `openid`, `chat_message.write`
* **Bot link feature**：`Normal` 或 `Aggressive`（開啟時提示加為官方帳號好友）
* **Google Maps API Key**：已綁定 `Maps JavaScript API`，並設定 `jerry910127.github.io/*` 網站參照限制防盜刷保護。

---

## 三、後端 Render 伺服器與 API 端點

後端採用 **FastAPI**，支援極速非同步處理與雙重備援推播機制：

### 1. 核心 API 端點清單
* `POST /webhook`
  * LINE 官方 Bot Webhook 接收點。
  * **非同步架構**：0.05 秒內完成驗簽並回傳 HTTP 200，透過 `BackgroundTasks` 在背景非同步呼叫 LLM，徹底避免 LINE 官方 1 秒超時重複發送問題。
* `POST /api/push_fortune`
  * 支援電腦瀏覽器、外開 Chrome / Edge，或 LIFF 缺少 `chat_message.write` 權限時，直接由伺服器端發起 `push_message`，將抽籤結果推送到信徒聊天室。
  * 傳入格式：`{"user_id": "U1234...", "text": "籤詩內容..."}`
* `POST /api/interpret_fortune`
  * 提供純網頁端免切換 LINE 的線上即時解籤 API。
  * 傳入格式：`{"text": "籤詩內容或問題"}`，回傳官方客觀解籤。
* `POST /api/touch_checkin`
  * 接收實體 LINE Touch (NFC 標籤) 碰觸打卡或前端打卡請求，記錄打卡軌跡並透過 LINE Messaging API 即時推播數位香火憑證到信眾聊天室。
  * 傳入格式：`{"user_id": "U1234...", "route_id": "wenchang", "checkpoint_index": 0}`
  * 回傳格式：`{"status": "ok", "message": "打卡成功", "checkpoint": "台北文昌宮", "pushed": true}`
* `GET /logs`
  * 伺服器日誌端點（保留最近 100 筆事件），方便免登入 Render 後台即時除錯。
* `GET /`
  * 服務健康檢查與版本狀態 (`{"version": "3.0.0", "status": "online"}`)。

---

## 四、LLM 模型與官方宮廟客服 Prompt 完整設定

### 1. 模型供應商與參數
* **供應商**：NVIDIA NIM (OpenAI Compatible API)
* **API Base URL**：`https://integrate.api.nvidia.com/v1`
* **模型名稱**：支援透過環境變數 `NVIDIA_MODEL` 動態指定，如 `meta/muse-glimmer-30b`、`meta/llama-3.2-11b-vision-instruct` 或 `moonshotai/kimi-k3`（後端內建 `reasoning_content` 思維鏈過濾與自動降級）
* **生成參數**：
  * 對話 `temperature`: `0.7`
  * 照片辨識 `temperature`: `0.7`
  * 一般對話 `max_tokens`: `256`（客服條理清晰）
  * 解籤分析 `max_tokens`: `512`（客觀文化析義）
  * 逾時設定 `timeout`: `8.0s ~ 15.0s`（若超時自動啟動廟方客服保底機制）

### 2. 官方宮廟客服 System Prompt（已上線正式版）
```text
你是「智慧宮廟線上服務處」的官方智能服務專員（兼具客觀文化執事與禮儀導引角色）。
請一律保持完全客觀、專業、禮貌、莊重且親切的「宮廟客服感」態度，為廣大信眾提供解答。

【核心原則與服務規範】：
1. 【語氣客觀中立、專業莊重】：
   - 自稱：「本處」、「廟方客服」、「線上服務專員」。
   - 稱呼信眾：「信士」、「信女」或「信眾您好」。
   - 態度：客觀理智、不宣力怪力亂神，恪守民俗文化引導者的角色，提供正向安定、心靈指引的建議。
2. 【日常互動與客服諮詢】：
   - 打招呼（哈囉/你好/早安）：「信士您好，歡迎光臨智慧宮廟線上服務處。請問今天有什麼民俗諮詢或求籤需求可以為您服務？」
   - 詢問在嗎/測試：「本處線上客服隨時為您服務。若有參拜禮節、線上求籤或籤詩釋義的需求，歡迎隨時提出。」
   - 發牢騷/疲倦/低潮：「人生旅程難免起伏，信士不妨稍作休歇、靜心調息。神明庇佑心誠則靈，若心有掛礙，亦可向神尊稟白祈福。」
3. 【主動引導求籤流程】：
   - 當信眾提及想抽籤、求籤、問事時，提供標準流程指引並附上專屬連結：
     「信士您好，若欲向神明祈願請示靈籤，請移步至智慧宮廟線上求籤專區：
     👉 https://liff.line.me/2011668576-3Qay1nBv
     【求籤指引】：心念姓名、農曆生辰與明確問事內容，搖動籤筒後需連續擲得『三個聖杯』方為應允正籤。求得籤詩後可回傳聊天室為您客觀解析。」
4. 【解籤客觀分析規範】：
   - 當信眾傳送籤詩內容時，以客觀、中立且兼具傳統文化內涵的角度進行條理拆解：
     - 【籤意主旨】：客觀陳述籤詩典故與卦象吉凶。
     - 【事情剖析】：就信眾所問之事（事業/感情/健康/運途）給予理性務實的建言。
     - 【廟方叮嚀】：提醒信士「事在人為，積德行善，心誠則靈」，切莫過度沉迷或盲信。
5. 【回覆規範】：
   - 條理分明、用字端正，統一使用繁體中文。
```

### 3. 照片視覺模型 System Prompt (Vision)
```text
你是智慧宮廟線上服務處的官方智能客服人員。信士傳送了一張照片（可能包含籤詩、神明聖像、平安符、香火袋或廟宇建築）。
請以客觀、禮貌、專業且莊重的客服語氣，用繁體中文為信士說明照片中的宗教文物象徵意義、文化由來與正向安定的提醒，篇幅適中、條理清晰。
```

### 4. 0.01 秒廟方客服秒回保底字典（Fallback Cache）
在 `backend/app.py` 中內建常用詞極速秒回：
* **招呼類 (嗨/哈囉)**：`"信士您好，歡迎光臨智慧宮廟線上服務處。請問今天有什麼能為您效勞？"`
* **詢問在嗎**：`"您好，本處線上客服隨時在線，竭誠為您服務。請問有參拜禮節或求籤指引的疑問嗎？"`
* **喊累喊煩**：`"信士辛苦了。日常勞碌之餘，不妨喝杯溫茶、放緩腳步靜心調息。神明護佑常在，願您順心安康。"`
* **問你是誰**：`"信士您好，我是智慧宮廟線上服務處的官方智能服務人員。隨時為您提供參拜諮詢、線上求籤導引與籤詩文化解讀。"`

---

## 五、前端心理學博弈與成癮保底機制

針對連續擲出「三聖杯」的機率疲乏問題，前端 [`index.html`](file:///C:/Users/user/Documents/line_AI2026/web_page/index.html) 實作了三大行為心理學機制：

### 1. 可變比率增強時制 (Variable-Ratio Schedule) 機率累加
* **基礎機率**：聖杯 50%、笑杯 25%、陰杯 25%。
* **微調遞增公式**：
  $$\text{聖杯機率} = \min(70\%, \; 50\% + (\text{failureStreak} \times 4\%) + \text{pityShengBonus})$$
  * 第 1 次未中：提升至 **54%**
  * 第 2 次未中：提升至 **58%**
  * 領取飲料券定心後：額外加成 $+5\%$，來到 **63% ~ 67%**
  * 上限封頂於 **70%**（黃金心流區間，維持 30% 懸疑與張力，不破壞真實博弈感）。
  * 達成連續 3 聖杯後，次數與加成自動歸零重置。

### 2. 近失效應 (Near-Miss Effect)
未獲聖杯時給予激勵型回饋，刺激多巴胺持續分泌：
* **笑杯**：`【笑杯】神明微笑傾聽・靈感蓄力中！`
* **陰杯**：`【陰杯】神明提點凝神・手氣漸旺！`
* **靈動蓄力標籤**：`✨ 誠心靈動共鳴值：58%（差臨門一腳，別收手！）`

### 3. 挫折補償與防流失 (飲品折扣券)
* **觸發時機**：連續擲筊失敗 2 次（耐性流失臨界點）。
* **彈窗補償**：彈出「🍵 喝口好茶，手氣正旺別放棄！」票券。
* **通用折扣碼**：`TEMPLE88`（全台合作手搖飲 / 咖啡通用現折 15 元或 85 折）。
* **一鍵續擲**：點擊「🥤 飲茶定心・一鼓作氣再擲！」即自動複製代碼、賦予 $+5\%$ 光環，且按鈕切換為「🔥 差一點！定心再擲」，原案零阻力繼續擲筊。

---

## 六、LINE Bye 三大核心頁面 UI 座標與業務邏輯架構

系統依據標準手機畫面比例（$X: 0\% \sim 100\%, Y: 0\% \sim 100\%$）規劃三大主頁面：

### 1. 頁面一：首頁（LINE Bye 萬春宮大墩開基主入口）
* **頂部導航列 (Header: $Y \approx 0\% \sim 8\%$)**：
  * `LINE BYE` 品牌標題 ($X \approx 5\% \sim 30\%, Y \approx 2\% \sim 7\%$)：`LINE` 為 `#2B1810`（沉穩檀木黑，1.35rem 粗體）；`BYE` 採用「聖筊圓弧半月造型」與「微笑嘴唇」結合之手繪向量底座（朱砂暗紅 `#981617` 外層、深緋紅 `#6B0A0D` 凹槽、豆沙肉粉 `#C97779` 微笑月牙光），中央以 HTML 獨立渲染**典雅金棕 `#C68F42` 的 `BYE` 文字（1.35rem 粗體，與 LINE 完全等大等重）**；右側搭配「萬春宮」專屬典雅金棕透光徽章。
  * 右側 4 圖示：優惠券（周邊商圈核銷，55%~70%）、說明 `?` (72%~78%)、即時消息鈴鐺 (80%~87%)、設定齒輪 (88%~95%)
* **主題推薦橫幅 (Hero Banner: $Y \approx 8\% \sim 32\%$)**：
  * 文案：「台中藍興媽祖 萬春宮」+「康熙六十年湄洲開基正身三媽・大墩三百載・護國庇民安」+ 金紅相映之開運香火平安扣向量插畫。
* **四大核心服務入口 (Quick Access Grid: $Y \approx 32\% \sim 45\%$)**：
  * `湄洲媽靈籤`（串 Web 抽籤擲筊＋連續三聖杯）
  * `祈安點燈`（線上填寫文疏＋LINE Pay 奉納＋殿前專屬虛擬元辰燈房）
  * `三百年巡禮`（**點擊直通頁面二**，實境文物走讀）
  * `白米收驚`（萬春宮傳承正統米卦安神儀軌＋誦咒安魂）
* **附近廟宇探索區 (Near Temples: $Y \approx 45\% \sim 75\%$)**：
  * 台中藍興媽祖萬春宮、台中第二市場（六角樓）、綠川柳川香路，標註 `📡 LINE Touch 感應`
* **底部跑馬燈橫條 (Footer Tips: $Y \approx 75\% \sim 83\%$)**：
  * 輪播新手參拜小撇步（右手插香、報家門、三聖筊等禮節）
* **底部付費廣告版位 (Ad Banner: $Y \approx 83\% \sim 92\%$)**：
  * 標註「付費廣告」，提供宮廟年度法會或伴手禮商家商業投放
* **底部五大導航欄 (Bottom Dock: $Y \approx 92\% \sim 100\%$)**：
  * 🏠 **首頁**：LINE Bye 萬春宮大墩開基入口
  * 🎋 **湄洲靈籤**：六十甲子籤詩＋連續三聖杯求籤儀軌
  * 🐉 **生肖歲煞**：五大凶星 AI 祭解排盤（五鬼、天狗、白虎、刑剋、空亡・即時測算本命歲煞與三媽開示）
  * 🎟️ **奉茶優惠**：周邊商圈心理學挫折奉茶優惠券
  * 👤 **信士中心**：參拜履歷與個人中心

---

### 2. 頁面二：參拜足跡總覽列表頁（Route Index）
* **頂部導航列 (Header: $Y \approx 0\% \sim 8\%$)**：
  * `‹` 返回鍵（圓形圖標按鈕，無多餘文字） ➔ 返回 LINE Bye 首頁
  * 標題「參拜足跡」($X \approx 35\% \sim 65\%$) ➔ 置中
  * `🏠` 首頁鍵（房子造型圖標按鈕，無多餘文字，取代原叉叉與回 LINE 文字） ➔ 一鍵返回主首頁
* **熱門推薦路線橫幅 (Hero Route Card: $Y \approx 10\% \sim 28\%$)**：
  * `[HOT] 核心推薦` 標籤 + 「萬春宮・三百年古蹟巡禮」+ `more >` 按鈕
* **直列主題路線卡片群 (Route Cards List: $Y \approx 30\% \sim 85\%$)**：
  * 卡片 1（萬春宮三百年古蹟巡禮，天后閣牌樓 ➔ 聖母大殿 ➔ 天井古鐘）
  * 卡片 2（1917 台中七媽會世紀香路，萬春宮、彰化南瑤、鹿港天后等百年聯庄）
  * 卡片 3（大墩二十四庄祈雨除災香路，嘉慶大旱祈雨靈驗神蹟・水神巡境行腳）
  * 卡片 4（中區舊城商圈走讀，第二市場、青草街、宮原眼科、手搖奉茶合作圈）
  * 點擊任一主題卡片 ➔ 攜帶路線 ID 跳轉至頁面三
* **底部常駐區 (Tips Bar: $Y \approx 85\% \sim 93\%$)**：參拜冷知識輪播

---

### 3. 頁面三：路線進度與打卡詳情頁（Route Detail）
* **頂部導航列 (Header: $Y \approx 0\% \sim 8\%$)**：
  * `‹` 返回鍵（圓形圖標按鈕，無多餘文字） ➔ 回列表頁
  * 路線標題（如「萬春宮古蹟巡禮」） ➔ 動態置中
  * `🏠` 首頁鍵（房子造型圖標按鈕，無多餘文字） ➔ 一鍵直通 LINE Bye 主首頁
* **進度狀態面板 (Progress Header: $Y \approx 10\% \sim 22\%$)**：
  * 大字置中：「目前已蒐集 X 個腳印」
  * 橢圓膠囊標籤：「共 3 個」
* **打卡站點清單與距離導引 (Checkpoints List: $Y \approx 24\% \sim 50\%$)**：
  * 萬春宮古蹟巡禮三大站點：
    * Ⓐ 萬春宮 天后閣牌樓（道光石獅）
    * Ⓑ 萬春宮 聖母大殿（光緒御匾）
    * Ⓒ 萬春宮 天井廊樓（咸豐古鐘・蒼龍壁畫）
  * 左側圓圈：已完成為綠色勾勾 `✓`，未完成為代號 Ⓐ / Ⓑ / Ⓒ
  * 右側即時計算實體直線距離（如 `距離 0.05 km`）
* **動態視覺化足跡地圖區 (Visual Track: $Y \approx 52\% \sim 95\%$)**：
  * **全面採用實體 Google Maps 足跡地圖（原卡通手繪「尋寶步道」已正式廢除）**：
    * 載入 Google Maps JavaScript API，以現代高質感地圖容器呈現萬春宮真實地理座標底圖（`lat: 24.1432, lng: 120.6806`，台中市中區成功路212號）。
    * **客製化足跡圖釘 (Custom Footprint Marker)**：
      * 未打卡站點：低對比質感灰色圖釘與微型腳印，標註站點代號（Ⓐ、Ⓑ、Ⓒ）。
      * 已打卡站點：亮綠色 / 金色常亮光環腳印圖釘，點擊彈出 InfoWindow 顯示站點名稱、打卡狀態與「🧭 Google 導航」按鈕。
    * **金色巡禮路徑 (Polyline)**：自動將各宮廟站點以金綠色平滑航線連接，標繪參拜信眾神聖進香軌跡。
    * **即時定位整合**：藍色即時 GPS 圓點動態標定信士所在位置，結合 LINE Touch 感應自動完成點亮打卡。
* **LINE Touch 實體 NFC 標籤規格與 URL 喚醒規範**：
  * 宮廟現場實體 NFC 晶片標籤（NTAG213 / NTAG215 等）寫入之 NDEF 網址格式：
    `https://liff.line.me/2011668576-3Qay1nBv?action=touch&route={route_id}&cp={checkpoint_index}`
    （例如：`https://liff.line.me/2011668576-3Qay1nBv?action=touch&route=wenchang&cp=0`）
  * **手機碰觸行為**：
    1. iOS / Android 感應到標籤後，自動以 LINE MINI App / LIFF 喚醒開啟「LINE Bye 智慧宮廟」。
    2. 前端 `checkLineTouchEntry()` 解析 URL 參數中的 `action=touch`、`route` 與 `cp`。
    3. 自動直接跳入該路線詳情頁（例如文昌宮路線）。
    4. 自動點亮對應站點足跡（腳印變金亮、進度累加、播放震動與音效）。
    5. 前端非同步呼叫後端 `/api/touch_checkin`，後端即時推播「🪔 參拜足跡打卡成功憑證」至信眾 LINE 聊天室，並附帶足跡地圖召回按鈕。
* **LINE Touch / 定位微型感應業務邏輯**：
  * GPS 即時測距：透過 `navigator.geolocation` 計算與廟宇直線距離
  * 當距離 $\le 50\text{m}$ 或點擊「📡 LINE Touch 打卡」/「模擬 LINE Touch 感應」時：
    1. 站點代號圓圈切換為打勾 `✓`
    2. 對應腳印點亮轉為綠色實線發光
    3. 頂部計數即時跳動（如 1/3 ➔ 2/3 ➔ 3/3 大圓滿）
    4. 震動回饋與彈出恭賀足跡解鎖提示
    5. 自動呼叫後端 `/api/touch_checkin` 推播數位憑證

---

## 七、歷史除錯紀錄與關鍵架構設計 (FAQ)

### 1. 權限報錯：`THE PERMISSION IS NOT IN LIFF APP SCOPE`
* **原因**：在手機端呼叫 `liff.sendMessages()` 時，LINE Developers 後台尚未審核通過或勾選 `chat_message.write` 權限。
* **解決方案**：前端採用雙層降級。若 `liff.sendMessages` 拋出錯誤，自動在 `catch` 中呼叫後端 `/api/push_fortune`，改由伺服器以 Channel Access Token 進行推播，用戶完全感知不到錯誤！

### 2. 電腦版無法回傳籤詩到聊天室？
* **原因**：外開瀏覽器或電腦端沒有原生 LINE 聊天視窗上下文。
* **解決方案**：透過 `liff.getProfile()` 取得 `userId`，呼叫後端 `/api/push_fortune`，手機端 LINE 聊天室秒收到籤詩與官方客觀解籤。

### 3. Render 免費層休眠 (Cold Start) 如何解決？
* **機制**：免費層 15 分鐘無請求會休眠，重啟需 30~50 秒。
* **處理方式**：
  * 前端加入即時狀態提示；
  * LINE Webhook 回傳 200 毫秒完成驗簽，避免被 LINE 官方中斷封鎖；
  * 可透過 UptimeRobot 或 CronJob 每 10 分鐘 `GET /` 保持常駐。

### 4. Git 分支管理規範
* GitHub Pages 預設服務分支：`main`。
* 建議每次更新執行同步推播指令：
  ```bash
  git push origin main && git push origin main:feat/temple-culture-v2
  ```

---
*本文件由開發代理自動生成與歸檔，所有金鑰與設定已完成校驗與備份。*
