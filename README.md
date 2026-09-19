# 🏮《靈籤入微：LINE 智慧宮廟文化生活圈》

> **「信仰心靈無價，便利科技賦能」** —— 專為解決年輕世代文化斷層、線上求籤儀式感薄弱、線下集章作弊，以及中小型在地宮廟缺乏數位曝光而打造的現代化智慧信仰生態。

---

## 📌 一、 專案核心定位與價值

* **競賽主題**：智慧校園 / 智慧零售 / 智慧照護 ➔ **加分主題：智慧宮廟**
* **核心痛點**：
  1. **參拜禮節斷層**：年輕世代走進宮廟常不知如何開口、報生辰八字、插香手勢或擲筊規矩。
  2. **傳統線上求籤失真**：現行線上求籤大多只是單純的「抽獎按鈕」，缺乏正統宮廟三聖筊確認的慎重與神聖感。
  3. **線下集章易作弊**：傳統紙本或 QR Code 集章容易代刷，無法確保信徒真正親臨宮廟巡禮。
  4. **中小型宮廟數位孤島**：資源有限的中小型特色宮廟無法自建 App，缺乏在地文化曝光管道。
* **解決方案**：
  * **極簡禪意 LIFF 微應用**：免下載 App，原創手繪檜木雙筊、竹籤筒與擬真拋物線擲杯，融入遊戲 Loading 式「參拜錦囊跑馬燈」。
  * **NVIDIA NIM 慈祥老廟祝**：採用低延遲 `z-ai/glm-5-3-flash` 大模型，將深奧文言籤詩轉化為溫暖現代生活指引。
  * **LINE Beacon 藍牙近場實體防作弊**：抵達宮廟現場自動觸發領取「廟宇小腳印／數位結緣書籤」，串聯老街商圈文化漫遊。

---

## 🏗️ 二、 系統架構全貌

```text
[ 信徒端 (LINE App) ]
  ├── 1. Rich Menu (圖文選單) ── 點擊開啟求籤入口
  ├── 2. LIFF 前端微應用 (GitHub Pages 託管)
  │      ├── 搖籤筒與三聖筊儀式感體驗 (原創日式/極簡禪風檜木向量素材)
  │      ├── 參拜禮節 Tips 跑馬燈 (解決拜拜小知識斷層)
  │      └── 一鍵發送籤文至聊天室 (liff.sendMessages)
  ├── 3. 後端 Webhook (Render 免費雲端託管)
  │      ├── FastAPI + line-bot-sdk v3 處理 Webhook
  │      ├── 調用 NVIDIA NIM 平台之 z-ai/glm-5-3-flash 大模型
  │      └── 慈祥老廟祝 Prompt 進行現代化、有溫度的生活解籤
  └── 4. 實體延伸：LINE Beacon (藍牙近場防作弊集章)
         └── 抵達宮廟現場自動觸發領取「數位結緣書籤 / 廟宇小腳印」
```

---

## 💻 三、 專案前後端配置清單

### 1. 前端（LIFF 求籤微應用）
* **GitHub 儲存庫**：`smart-temple-liff`
* **部署平台**：GitHub Pages
* **正式網址**：[https://jerry910127.github.io/smart-temple-liff/](https://jerry910127.github.io/smart-temple-liff/)
* **LIFF ID**：`2011668576-3Qay1nBv`
* **LIFF URL**：[https://liff.line.me/2011668576-3Qay1nBv](https://liff.line.me/2011668576-3Qay1nBv)
* **設計亮點**：
  * **原創無版權疑慮**：全純手繪向量 SVG（天然檜木紋月牙雙筊、日式六角籤筒、朱漆靈籤），徹底杜絕照片侵權。
  * **參拜錦囊跑馬燈**：輪播插香手勢、生辰八字報法、龍進虎出動線、三聖筊神意驗證等民俗冷知識。
  * **擬真物理動效**：完整重現下沉蓄力、仰角飛天、空中 720°~900° 翻轉與 Web Audio 落地碰撞聲。

### 2. 後端（AI 智慧廟祝 Webhook）
* **目錄位置**：[backend/](file:///C:/Users/user/Documents/line_AI2026/web_page/backend/)
* **部署平台**：Render (Web Service, Free Instance, Region: Singapore)
* **核心技術**：Python 3.10+, FastAPI, line-bot-sdk v3, OpenAI SDK (NVIDIA NIM)
* **檔案說明**：
  * [app.py](file:///C:/Users/user/Documents/line_AI2026/web_page/backend/app.py)：FastAPI Webhook 服務與老廟祝 Prompt 核心邏輯。
  * [requirements.txt](file:///C:/Users/user/Documents/line_AI2026/web_page/backend/requirements.txt)：專案相依套件。
  * [Procfile](file:///C:/Users/user/Documents/line_AI2026/web_page/backend/Procfile)：Render 啟動配置 `web: uvicorn app:app --host 0.0.0.0 --port $PORT`。
  * [.env.example](file:///C:/Users/user/Documents/line_AI2026/web_page/backend/.env.example)：環境變數範本。
* **環境變數配置**：
  * `LINE_CHANNEL_SECRET`：LINE 頻道密鑰
  * `LINE_CHANNEL_ACCESS_TOKEN`：LINE 頻道訪問憑證
  * `NVIDIA_API_KEY`：NVIDIA NIM API Key (`nvapi-...`)
* **AI 大模型配置**：
  * 平台：NVIDIA NIM API Catalog
  * 模型：`z-ai/glm-5-3-flash`
  * 優勢：低延遲、原生中文語感優異，精準理解文言籤詩並轉化為溫暖白話指引。

---

## 💼 四、 商業模式與運營規劃（扣合競賽 20% 商模指標）

1. **線上代辦點燈便利手續費**：
   * 整合光明燈、太歲燈、文昌燈線上登錄與 LINE Pay 支付。
   * 廟方原價收取香油錢/燈費，平台收取小額代辦行政服務費（例：每盞 30~50 元），完成後自動推播數位感謝憑證與安燈照片。
2. **LINE 宮廟文化訂閱服務**：
   * 提供「初一十五拜拜推播提醒」、「二十四節氣養生開運小撇步」、「民間信仰趣味小知識」。
   * 建立高黏著度的信徒文化社群。
3. **地方特色宮廟聯合賦能（B2B2C）**：
   * 透過 LINE Beacon「廟宇小腳印」串聯全台特色中小型宮廟與周邊老街商圈。
   * 提供信徒打卡集章換商圈折價券，有效導引觀光客流，振興在地文化經濟。

---

## 🛡️ 五、 安全分支管理說明

本項目目前於獨立分支 **`feat/temple-culture-v2`** 進行改動與維護：
* 若需還原回上一版本，隨時可切換回 `main` 分支：
  ```bash
  git checkout main
  ```
* 確保開發、實驗與簡報展示安全無虞！
