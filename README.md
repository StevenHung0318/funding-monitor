# Funding Rate Monitor

監控幣安 & OKX 資費結算間隔變化，變化時發送 Telegram 通知。

## 設定

1. Fork 這個 repo
2. 到 Settings → Secrets and variables → Actions
3. 新增兩個 secrets：
   - `TG_BOT_TOKEN`: 你的 Telegram Bot Token
   - `TG_CHAT_ID`: 你的群組 ID

## 執行

- 自動：每 10 分鐘執行一次
- 手動：Actions → Funding Rate Monitor → Run workflow
