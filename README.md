# LINEBYE 智慧宮廟文化生活圈

以台中萬春宮為核心的 LINE LIFF / MINI App 原型，整合宮廟文化導覽、線上靈籤、AI 解籤、正念念珠、祈安點燈及《藍興之謎：尋找遺失的寶物》六關實境尋寶。

目前版本：`v3.8.1`（神祕探索介面＋免費試玩序章，本機原型）

## v3.8.1 免費試玩序章

- 首頁「藍興之謎」→「拆開三張殘頁・免費試玩序章」；直接預覽可用 `http://127.0.0.1:8765/?page=quest`。
- 「她曾有另一個名字」以三張殘頁排序串起萬春宮的一段歷史；答對才揭曉舊稱，不預先公開後續任務、地圖位置或終章小物。保留原本深色信封、金色字樣與紙頁風格。
- 支援提示、退回上一段、暫離／重新整理續玩、完成後重讀及重玩。進度獨立存於 `wanchun_quest_prologue_v1`；重玩不刪除先前發現，也不變更正式走讀印記或啟動資格。
- 新序章不設定舊版 `wanchun_quest_trial`，不解鎖正式關卡；保留既有舊版第一關試玩者及付費玩家的進度與存取規則。
- 序章無須定位、啟動碼或 LINE 登入。若儲存失敗，仍可當次試玩並顯示提醒。原 App 的周邊定位功能維持不變。
- 史料：[臺中市文化局・萬春宮與藍廷珍](https://www.culture.taichung.gov.tw/2187646/post)。殘頁與翻面為創作，非出土文書；本功能為尚待廟方確認的提案原型，不代表正式合作、活動或核銷承諾。
- 驗證：`node tests/quest-mystery.test.cjs`；啟動本機伺服器後，已安裝 Playwright 與 Edge 的環境可執行 `node tests/quest-prologue.browser.test.cjs`。後者隔離外部服務，涵蓋答錯、提示、續玩、重玩、舊進度、損毀存檔、儲存失敗、鍵盤與 320／390／768px 排版。
- 本次僅修改本機前端，未部署 GitHub Pages／LIFF，未修改後端。

## 產品洞察與定位

### 我們發現的問題

傳統解謎包多以題本、紙盒與一次性道具組成，遊戲結束後常被丟棄；參與者帶走的多半只有短暫體驗，文化內容、廟宇連結與地方消費也難以延續。

### 解決方案

LINEBYE 把一次性的實體題盒改為 LINE 上的數位體驗。信眾可以先在線上認識參拜流程、祈願與地方故事；有機會到訪台中萬春宮時，再遊玩《藍興之謎：尋找遺失的寶物》，沿著廟宇、舊城與商圈完成六道任務。通關後，故事中的「遺失寶物」化為《藍興之謎》通關限定版聖筊擺飾，讓玩家把故事帶回家；擺飾底座內建 NFC，手機靠近即可再次開啟 LINEBYE，讓體驗從遊戲延續到日常。擺飾定位為文創紀念品，不宣稱保平安或開光。

### 商業模式

- 遊戲體驗：以啟動碼提供付費數位尋寶內容，降低印刷、包裝與一次性道具成本。
- 文創商品：聖筊擺飾分兩版。通關限定版只能完成解謎取得；一般版販售（提案價 199 元，成本約 50 元），與宮廟分潤。正式品項與核銷方式由合作廟方確認。
- 商圈導流：謎題串聯青草街、第二市場、繼光街等節點，把參與者的步行路線轉化為地方店家的來客機會。
- 合作收入：可延伸廟方、商圈店家與地方活動的聯名、贊助及限定任務合作。
- 長期關係：透過 LINE 持續提供線上參拜、文化內容、活動通知與回訪任務，讓一次遊戲成為認識台中與再次到訪的入口。

### v3.8 神祕探索介面

- 首頁以未署名的信與封口意象吸引探索，只暗示「神祕小物」，不提前展示終章獎品。
- 序章提供首段免費體驗、約 90 分鐘步行資訊、費用及活動核驗說明；故事保密，參與規則明確。
- 每次僅呈現目前線索，已完成內容收進「我的發現」，後續地點與任務不渲染。
- 啟動碼只提供參與資格，不解除順序限制；地圖與導航共用逐關顯示條件。地圖授權失敗時提供誠實標示的線索位置卡。
- 答題後先閱讀文化故事與下一段懸念，再手動繼續；全部完成後主動揭開終章小物。
- GPS／Touch 僅引導到場，不自動解題；答案欄不再洩漏正解，驗證採已列出的答案別名精確比對。
- 回歸測試：`node tests/quest-mystery.test.cjs`。本地儲存只支援原型敘事進度，不是防作弊或正式核銷憑證；未修改後端核銷或部署。

## 系統架構

```text
LINE / 瀏覽器
  └─ GitHub Pages：index.html 單頁 LIFF 前端
       ├─ 萬春宮首頁與信眾服務
       ├─ 搖籤、三聖筊與籤詩卡
       ├─ Google Maps / GPS 實境解謎
       └─ LIFF ID token
              │
              ▼
Render：FastAPI 後端
  ├─ LINE Webhook 與 Messaging API
  ├─ NVIDIA NIM 文字／圖片解讀
  ├─ LINE ID token 驗證
  └─ 啟動碼、速率限制與受保護日誌
```

## 主要檔案

- `index.html`：前端 SPA、LIFF、靈籤、念珠、點燈、地圖與實境解謎。
- `backend/app.py`：FastAPI、LINE Webhook、AI 解籤、推播、打卡與安全驗證。
- `backend/render.yaml`：Render 部署設定。
- `backend/generate_richmenu.py`：產生 2500 × 1686 LINE Rich Menu 圖片。
- `backend/deploy_richmenu.py`：建立、上傳並套用 LINE Rich Menu。
- `assets/`：圖示、貼圖、籤筒與擲筊素材。

## 正式網址

- GitHub Pages：https://jerry910127.github.io/smart-temple-liff/
- LIFF：https://liff.line.me/2011668576-3Qay1nBv
- 後端：https://smart-temple-liff.onrender.com
- Webhook：https://smart-temple-liff.onrender.com/webhook

## 後端環境變數

複製 `backend/.env.example` 為本機 `.env`，正式環境則在 Render 設定：

- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `NVIDIA_API_KEY`
- `NVIDIA_MODEL`
- `LINE_LOGIN_CHANNEL_IDS`：允許驗證的 LINE Login / MINI App Channel ID。
- `ALLOWED_ORIGINS`：允許呼叫後端的前端來源，以逗號分隔。
- `ADMIN_LOG_TOKEN`：讀取 `/logs` 時使用的 `X-Admin-Token`。
- `QUEST_ACCESS_CODE_HASHES`：有效啟動碼的 SHA-256 雜湊，以逗號分隔。

產生啟動碼雜湊範例：

```powershell
python -c "import hashlib; print(hashlib.sha256(b'YOUR-CODE').hexdigest())"
```

不要將啟動碼明碼、LINE Token 或 NVIDIA API Key 提交到 Git。

## 本機執行

前端：

```powershell
python -m http.server 8765 --directory .
```

後端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

若前端要從 `http://127.0.0.1:8765` 呼叫本機或正式後端，需暫時把該來源加入 `ALLOWED_ORIGINS`。LINE LIFF 與 Google Maps 仍會依各平台控制台的 Endpoint URL／HTTP referrer 限制判斷。

## API

- `POST /webhook`：LINE 簽章驗證後處理訊息與 FollowEvent。
- `POST /api/push_fortune`：驗證 LIFF ID token 後推送籤詩並排程 AI 解籤。
- `POST /api/touch_checkin`：驗證 LIFF ID token 後推送實境解謎通關通知。
- `POST /api/interpret_fortune`：文字解籤；具有長度與速率限制。
- `POST /api/quest/activate`：以後端 SHA-256 雜湊清單驗證啟動碼。
- `GET /logs`：需 `X-Admin-Token`；未設定管理密鑰時回傳 404。
- `GET /`：健康檢查與版本資訊。

依 LINE 官方安全建議，使用者身分由前端傳送原始 `liff.getIDToken()`，後端呼叫 LINE 驗證端點並採用驗證結果中的 `sub`；後端不信任前端自行提供的 user ID。

## 已知限制

- 實境走讀進度仍保存在瀏覽器 `localStorage`，適合展示與試營運，不足以作為不可偽造的正式兌換紀錄。正式核銷應新增資料庫、伺服器端關卡驗證與一次性兌換狀態。
- Google Maps Browser API key 必須出現在靜態前端；請在 Google Cloud Console嚴格限制網域、API 類型與配額，並定期輪替。
- Render 免費方案可能休眠，首次請求可能有冷啟動延遲。
- 提案中的 AI Marketing Engine／ComfyUI 內容工廠不在此儲存庫中；本儲存庫目前實作 LINEBYE 使用者端與 LINE Bot 後端。
