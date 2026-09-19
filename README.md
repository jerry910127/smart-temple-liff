# 🏮 智慧宮廟 - LINE LIFF 線上求籤前端

以純 HTML/CSS/JavaScript 與 LINE LIFF SDK 打造的沉浸式線上擲筊求籤體驗，可直接透過 GitHub Pages 託管並在 LINE App 內直接開啟使用。

## 📁 檔案說明
- [index.html](file:///C:/Users/user/Documents/line_AI2026/web_page/index.html)：求籤主頁面，包含：
  - LIFF SDK 自動初始化與身份驗證
  - 祈福求籤與聖筊動畫
  - `liff.sendMessages` 自動將籤文傳回聊天室
  - 完成後自動關閉 LIFF 視窗

## 🚀 部署與設定指引

### 1. 替換 LIFF ID
開啟 [index.html](file:///C:/Users/user/Documents/line_AI2026/web_page/index.html)，找到：
```javascript
const MY_LIFF_ID = "YOUR_LIFF_ID";
```
將 `YOUR_LIFF_ID` 替換為你在 [LINE Developers Console](https://developers.line.biz/) 建立的 LIFF ID。

### 2. 推送至 GitHub
```bash
git init
git add .
git commit -m "feat: initial commit for smart temple liff"
git branch -M main
git remote add origin https://github.com/<你的GitHub帳號>/<你的儲存庫名稱>.git
git push -u origin main
```

### 3. 開啟 GitHub Pages
1. 在 GitHub 進入該 Repo 的 **Settings** -> **Pages**。
2. **Branch** 選擇 `main`，路徑保持 `/ (root)`，點擊 **Save**。
3. 取得網址：`https://<你的GitHub帳號>.github.io/<你的儲存庫名稱>/`。

### 4. 設定 LINE Developers Endpoint URL
- 將取得的 GitHub Pages 網址填入 LIFF App 的 **Endpoint URL**。
- 複製 `https://liff.line.me/<LIFF_ID>` 連結，在 LINE 中點擊即可測試！
