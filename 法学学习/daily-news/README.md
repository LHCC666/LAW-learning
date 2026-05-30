# 📰 每日新闻简报 — 配置指南

## 第一步：安装 Python 依赖（仅本地测试需要）

```bash
cd 法学学习/daily-news
pip install -r requirements.txt
```

## 第二步：获取 Gmail 应用专用密码 🔑

> ⚠️ 不能用你的 Gmail 登录密码，必须用「应用专用密码」

1. 打开 [Google 账号安全性](https://myaccount.google.com/security)
2. 确保 **两步验证** 已开启（没开的话先开启）
3. 在两步验证下方找到 **应用专用密码**（App Passwords）
   - 或直接访问：https://myaccount.google.com/apppasswords
4. 随便起个名字，比如 `新闻简报`
5. 点 **创建** → 弹出 16 位密码（格式：`xxxx xxxx xxxx xxxx`）
6. **复制下来！** 关闭后就再也看不到了

## 第三步：修改 config.json（仅本地测试需要）

```json
{
    "max_items": 7,
    "to_email": "你的邮箱@gmail.com",
    "smtp": {
        "server": "smtp.gmail.com",
        "port": 587,
        "sender_email": "你的邮箱@gmail.com",
        "auth_code": "xxxxxxxxxxxxxxxx"
    }
}
```

- `to_email`：接收新闻的邮箱
- `sender_email`：发件的 Gmail
- `auth_code`：上一步的 16 位应用密码（去掉空格）

## 第四步：在 GitHub 设置 Secrets

打开 https://github.com/LHCC666/first-try-/settings/secrets/actions

点 **New repository secret**，添加 3 个：

| Secret 名 | 值 |
|-----------|-----|
| `TO_EMAIL` | `你的邮箱@gmail.com` |
| `SENDER_EMAIL` | `你的邮箱@gmail.com` |
| `AUTH_CODE` | `16位应用密码（去掉空格）` |

## 第五步：提交代码 → 自动运行 ☁️

```bash
cd D:\ccuurroo
git add .
git commit -m "添加每日新闻简报（Gmail + GitHub Actions）"
git push origin main
```

Push 之后每天早上 8:07（北京时间）自动发送 📧

## 🧪 手动测试

1. 打开 https://github.com/LHCC666/first-try-/actions
2. 左侧点 **每日新闻简报**
3. 点 **Run workflow** → **Run workflow**
4. 等 1-2 分钟，查收邮件

---

## 自定义

### 调整新闻数量
修改 `config.json` 中 `max_items`（建议 5-10），或在 workflow YAML 中改 `cfg` 里的值。

### 调整发送时间
编辑 `.github/workflows/daily-news.yml` 中的 cron：
- 目前是 `7 0 * * *`（UTC 0:07 = 北京时间 8:07）
- 比如改成 `7 22 * * *` = 北京时间早上 6:07

### 添加/删除新闻源
编辑 `daily_news.py` 中的 `RSS_SOURCES` 和 `WEB_SOURCES`。

---

## 故障排查

| 问题 | 解决 |
|------|------|
| 收不到邮件 | 检查 Gmail 垃圾箱、确认 Secrets 拼写正确 |
| 认证失败 | 确认是应用专用密码而非登录密码 |
| Gmail 拒绝 | 确认两步验证已开启 |
| 抓不到新闻 | GitHub Actions 的服务器在国外，部分中文源可能慢 |
| 想换回 QQ | config 里 server 改 `smtp.qq.com`，port 改 `465` |
