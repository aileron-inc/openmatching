# OpenCode Matching System

OpenCode AI を使った人材マッチングシステム

## 📁 プロジェクト構造

```
opencode-matching/
├── bin/                # 実行スクリプト
│   ├── download.py     # データダウンロード＆NDJSON変換
│   ├── job.py          # 求人マッチング
│   ├── company.py      # 企業検索
│   ├── bot.py          # Slackボット（オプション）
│   └── updater.py      # GitHub更新ツール
│
├── tmp/                # CSVダウンロード先（一時ファイル）
└── workspace/          # OpenCode作業スペース
    ├── AGENTS.md       # OpenCode指示書
    ├── *.ndjson        # データファイル
    └── output/         # マッチング結果
```

## 🚀 使い方

### 1. データダウンロード（定期実行推奨）

```bash
uv run bin/download.py
```

Salesforce からデータをダウンロードし、workspace/ に NDJSON 配置します。

**環境変数:**
- `SALESFORCE_CREDENTIALS` (required): Salesforce認証情報（JSON形式）
- `RECENT_INTERVIEW_DAYS` (optional, default: 60): 初回面談日フィルタ（日数）
- `MIN_SURVEY_YEAR` (optional, default: 2024): アンケート回答年フィルタ
- `VALID_RANKS` (optional, default: S,A,B): 登録時ランクフィルタ
- `JOB_STATUS` (optional, default: アクティブ): 求人状態フィルタ

### 2. 求人マッチング

```bash
uv run bin/job.py J-0000023845
uv run bin/job.py 23845           # 数字のみでもOK
```

求人IDに合う候補者をマッチングします。

### 3. 企業検索

```bash
uv run bin/company.py "SaaS系スタートアップ" 10
uv run bin/company.py "週1出社" 20
```

条件に合う企業を検索します。

### 4. Slackボット（オプション）

```bash
uv run bin/bot.py
```

Slack から上記機能を実行できます。

**必要な環境変数:**
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`

## 🔧 セットアップ

### 初回のみ

```bash
# 1. 環境変数設定
cp .env.example .env
# .env を編集して必要な環境変数を設定

# 2. データダウンロード
uv run bin/download.py
```

### 定期実行（cron例）

```bash
# 毎日 8:00 にデータ更新
0 8 * * * cd /path/to/opencode-matching && uv run bin/download.py
```

## 📝 出力

マッチング結果は `workspace/output/` に保存されます：

- `matching_YYYYMMDD_HHMMSS.csv` - 求人マッチング結果
- `matching_YYYYMMDD_HHMMSS_summary.md` - マッチングサマリー
- `companies_YYYYMMDD_HHMMSS.csv` - 企業検索結果
- `companies_YYYYMMDD_HHMMSS_summary.md` - 企業検索サマリー

## 🤖 OpenCode について

このプロジェクトは OpenCode AI を使用しています。

- マッチングロジックは `workspace/AGENTS.md` に記載
- OpenCode は `workspace/` ディレクトリ内で実行され、完結します
