### C. CLI 工具與查詢模擬

使用技術：
- Python CLI 工具（argparse, requests）
- 使用者互動輸入、查詢條件構造
- API 回應處理、錯誤顯示、log 紀錄

負責內容：
- 完整建構 CLI 查詢流程（輸入出發地、目的地、時間等）
- 整合參數輸入（token、interval），顯示等級與查詢配額
- 整合即時動態資料模擬：每隔一段時間動態產生假航班資訊並即時排序顯示，模擬查票與票價變化過程
- 設計依據使用者權限（Free / Plus / Pro）**調整資料生成速度與密度**，如：
  - Free：每 5 秒 1 筆
  - Plus：每 3 秒 2 筆
  - Pro：每秒 3 筆，模擬高頻查詢情境
- 撰寫獨立模組 `flight_generator.py`，集中處理假資料生成邏輯，供主查詢工具與異常模擬工具共用
- 設計 log 寫入與紀錄格式，協助系統層判斷封鎖條件

對應檔案結構：
cli/
├── ticket-checker.py
├── log_writer.py
├── flight_generator.py
logs/
├── user_token.log