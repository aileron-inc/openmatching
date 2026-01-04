# OpenMatching デプロイガイド

DigitalOcean VPS（Ubuntu）へのシンプルなデプロイ手順です。

## 📋 前提条件

- Ubuntu 20.04 以上のVPS
- SSH公開鍵認証で接続可能
- sudo権限を持つユーザー（例: ubuntu）

## 🚀 デプロイ手順

### 1. VPSにディレクトリ作成

```bash
ssh ubuntu@your-vps-ip
sudo mkdir -p /opt/openmatching
sudo chown ubuntu:ubuntu /opt/openmatching
exit
```

### 2. コードを転送

```bash
# プロジェクトルートから実行
rsync -avz --exclude '.git' --exclude '.env' --exclude '__pycache__' --exclude '.venv' --exclude 'tmp/*' --exclude 'workspace/output/*' \
  . ubuntu@your-vps-ip:/opt/openmatching/
```

### 3. 環境変数を転送

```bash
# .envファイルを作成（.env.exampleを参考に）
scp .env ubuntu@your-vps-ip:/opt/openmatching/.env
```

### 4. セットアップ実行

```bash
ssh ubuntu@your-vps-ip "sudo bash /opt/openmatching/deploy/setup.sh"
```

### 5. 動作確認

```bash
# ログをリアルタイム表示
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot -f"
```

---

## 🔄 更新時のデプロイ

コードを修正した後:

```bash
# コード転送
rsync -avz --exclude '.git' --exclude '.env' --exclude '__pycache__' --exclude '.venv' --exclude 'tmp/*' --exclude 'workspace/output/*' \
  . ubuntu@your-vps-ip:/opt/openmatching/

# サービス再起動
ssh ubuntu@your-vps-ip "sudo systemctl restart openmatching-bot"
```

---

## 🛠️ 便利なコマンド

### サービス管理

```bash
# 状態確認
ssh ubuntu@your-vps-ip "sudo systemctl status openmatching-bot"

# 再起動
ssh ubuntu@your-vps-ip "sudo systemctl restart openmatching-bot"

# 停止
ssh ubuntu@your-vps-ip "sudo systemctl stop openmatching-bot"

# 起動
ssh ubuntu@your-vps-ip "sudo systemctl start openmatching-bot"
```

### ログ確認

```bash
# リアルタイムログ
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot -f"

# 最新100行
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot -n 100"

# エラーのみ
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot -p err"
```

### ヘルスチェック

Slackで `@bot ping` と送信すると、botの稼働状況を確認できます。

---

## 📊 監視

- 毎朝8時に自動的にデータダウンロードが実行され、Slackに完了通知が送られます
- 通知が来ない場合、botが停止している可能性があります
- `@bot ping` コマンドでいつでもヘルスチェック可能です

---

## 🔧 カスタマイズ

### ダウンロード実行時刻を変更

`bin/bot.py` の以下の行を編集:

```python
schedule.every().day.at("08:00").do(run_download)
# ↓ 例: 22時に変更
schedule.every().day.at("22:00").do(run_download)
```

変更後、デプロイして再起動してください。

### 通知先チャンネルを変更

`.env` ファイルの `SLACK_CH` を変更:

```bash
SLACK_CH=C12345ABC  # 別のチャンネルID
```

---

## 🚨 トラブルシューティング

### botが起動しない

```bash
# エラーログ確認
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot -n 50"

# 手動実行してエラー確認
ssh ubuntu@your-vps-ip
cd /opt/openmatching
uv run bin/bot.py
```

### 環境変数が読み込まれない

```bash
# .envファイルの存在確認
ssh ubuntu@your-vps-ip "ls -la /opt/openmatching/.env"

# 内容確認（秘匿情報注意）
ssh ubuntu@your-vps-ip "head /opt/openmatching/.env"
```

### OpenCode CLIが見つからない

```bash
# パス確認
ssh ubuntu@your-vps-ip "which opencode"

# 再インストール
ssh ubuntu@your-vps-ip "curl -fsSL https://opencode.ai/install | bash"
```

### 定期実行が動かない

```bash
# スケジューラーのログ確認
ssh ubuntu@your-vps-ip "sudo journalctl -u openmatching-bot | grep '定期実行'"

# bot再起動
ssh ubuntu@your-vps-ip "sudo systemctl restart openmatching-bot"
```

---

## 📝 他のプロジェクトへの応用

この構成は以下の要件を持つプロジェクトで再利用できます:

- **uv** でPython依存関係を管理
- **OpenCode CLI** を使用
- **Slackボット** で常駐プロセスが必要
- **定期実行** が必要（bot内スケジューラーで実装）

### 応用方法

1. `bin/` のスクリプトを書き換え
2. `workspace/AGENTS.md` を書き換え
3. `.env.example` を編集
4. デプロイ実行

それだけです。

---

## 🎯 アーキテクチャ

```
┌─────────────────────────────────────┐
│    Slack Bot (常駐プロセス)          │
│  ┌──────────────────────────────┐   │
│  │  メンション処理                 │   │
│  │  - job (求人マッチング)         │   │
│  │  - company (企業探索)          │   │
│  │  - ping (ヘルスチェック)        │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  スケジューラー (定期実行)       │   │
│  │  - 毎日8時: download.py実行    │   │
│  │  - 結果をSlackに通知            │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
         ↓ 全てSlackに通知
    ┌──────────┐
    │  Slack   │
    └──────────┘
```

**ポイント:**
- cron不要、botが全て内包
- 全てのエラーと成功がSlackに通知される
- シンプルなSSH操作でデプロイ可能
