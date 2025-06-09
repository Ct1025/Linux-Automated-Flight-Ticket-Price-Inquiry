### B. API 設計與帳號 / 權限管理

使用技術：
- Flask / FastAPI
- JSON 檔處理（帳號、權限、token）
- 權限分級與配額邏輯控制（free / plus / pro）

負責內容：
- 建立 `users.json` 帳號系統，管理帳號、密碼、token 與權限等級
- 撰寫 CLI 帳號註冊工具（輸入帳密與等級 → 自動產生 token）
- 製作 `/user-info` API，查詢使用者權限與剩餘查詢額度
- 實施速率限制機制，根據用戶等級設定不同的請求頻率限制：
  - **Free 用戶**: 每分鐘最多 15 次請求，查詢間隔 6 秒
  - **Plus 用戶**: 每分鐘最多 25 次請求，查詢間隔 4 秒  
  - **Pro 用戶**: 每分鐘最多 100 次請求，查詢間隔 2 秒

對應檔案結構：
api/
├── api_server.py
├── user_info.py
├── token_config.json
data/
├── users.json
tools/
├── register.py

cli-checker.md