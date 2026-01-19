# OpenCode Workspace - Agent Instructions

このディレクトリは OpenCode による AI マッチング処理専用のワークスペースです。

## 📂 ディレクトリ構成

```
workspace/
├── data/
│   ├── candidates_rank_A.ndjson     # 求職者データ（ランクA）
│   ├── candidates_rank_B.ndjson     # 求職者データ（ランクB）
│   ├── jobs_human_resources_A.ndjson # 求人票（人材・ランクA）
│   ├── jobs_human_resources_B.ndjson # 求人票（人材・ランクB）
│   ├── jobs_human_resources_C.ndjson # 求人票（人材・ランクC）
│   ├── jobs_it_services_A.ndjson    # 求人票（IT総合・ランクA）
│   ├── jobs_it_services_B.ndjson    # 求人票（IT総合・ランクB）
│   ├── jobs_it_services_C.ndjson    # 求人票（IT総合・ランクC）
│   ├── jobs_it_services_S.ndjson    # 求人票（IT総合・ランクS）
│   ├── jobs_other_A.ndjson          # 求人票（その他・ランクA）
│   ├── jobs_other_B.ndjson          # 求人票（その他・ランクB）
│   ├── jobs_other_C.ndjson          # 求人票（その他・ランクC）
│   ├── jobs_other_S.ndjson          # 求人票（その他・ランクS）
│   ├── companies_human_resources_A.ndjson # 企業（人材・ランクA）
│   ├── companies_human_resources_B.ndjson # 企業（人材・ランクB）
│   ├── companies_human_resources_C.ndjson # 企業（人材・ランクC）
│   ├── companies_it_services_A.ndjson # 企業（IT総合・ランクA）
│   ├── companies_it_services_B.ndjson # 企業（IT総合・ランクB）
│   ├── companies_it_services_C.ndjson # 企業（IT総合・ランクC）
│   ├── companies_other_A.ndjson    # 企業（その他・ランクA）
│   ├── companies_other_B.ndjson    # 企業（その他・ランクB）
│   ├── companies_other_C.ndjson    # 企業（その他・ランクC）
│   └── ...
├── output/
│   ├── matching_*.csv              # マッチング結果
│   ├── matching_*_summary.md       # サマリー
│   ├── companies_*.csv             # 企業探索結果
│   └── companies_*_summary.md      # サマリー
├── text/
│   └── *_*.txt                     # テキスト形式コピー（参照用）
└── AGENTS.md                        # このファイル
```

## ⚠️ 重要：作業範囲の制限

**このワークスペース（workspace/）の data/ ディレクトリ内のファイルのみにアクセスしてください。**

- ✅ アクセス可能: `data/candidates_rank_*.ndjson`, `data/jobs_*.ndjson`, `data/companies_*.ndjson`, `output/`
- ❌ アクセス禁止: 親ディレクトリ（`../`）やプロジェクトルートのファイル
- ❌ 禁止例: `../job.py`, `../download.py`, `../bot.py` など
- ❌ 権限要求禁止: workspace/ 外のファイルへのアクセス権限を求めない

**全ての処理は workspace/ ディレクトリ内で完結させること。**

---

## 📁 ファイル構成

### 入力データ
- `candidates_rank_*.ndjson` - 求職者データ（ランク別分割済み）
- `jobs_*.ndjson` - 求人票データ（業種・ランク別分割済み）
- `companies_*.ndjson` - 企業データ（業種・ランク別分割済み）

### 業種分類
- `human_resources` - 人材業界
- `it_services` - IT総合
- `other` - その他

### ランク分類
- `S`, `A`, `B`, `C`, `D`, `N`, `P` - 企業ランク
- `affiliated` - 関連会社
- `defunct` - 廃業（処理対象外）

### 出力先
- `output/` - マッチング結果・企業探索結果の出力先
  - `matching_*.csv` - 求人レコメンド結果
  - `matching_*_summary.md` - 求人レコメンドサマリー
  - `companies_*.csv` - 企業探索結果
  - `companies_*_summary.md` - 企業探索サマリー

### 参照データ
- `text/` - ndjsonファイルのテキスト形式コピー（参照用）

---

## 🎯 処理の原則

### データの整合性
- CSV、サマリー、ターミナル出力の件数は完全に一致させる
- CSVに89社書いたら、サマリーにも89社全てリストアップし、「検索結果総数: 89社」と明記
- 数字の不一致は絶対に起こさない

### 出力形式
- Salesforce URLは必ず Markdown リンク形式で出力
- 例: `[候補者を開く](https://your-org.lightning.force.com/lightning/r/Contact/{ID}/view)`
- 注意: 実際のURLは環境変数 SALESFORCE_BASE_URL から取得されます

### フィルタリング（企業探索）
検索クエリに「週N出社」などの出社頻度が含まれる場合、**数値的に厳密に判定**すること：

1. **出社頻度の数値抽出ルール:**
   - 「フルリモート」「リモートワークOK」 → 出社0日
   - 「週1出社」 → 出社1日
   - 「週1~2出社」 → 出社2日（範囲の場合は**最大値**を採用）
   - 「週2~3出社」 → 出社3日
   - 「週3出社」 → 出社3日
   - 「月1~2回出社」 → 出社0.5日（週換算）
   - 「リモートワーク可能/頻度要確認」など曖昧な表記 → 数値不明として除外

2. **フィルタリング条件:**
   - 検索クエリが「週1出社」の場合 → 出社日数が**1日以下**の企業のみ選定
   - 検索クエリが「週2出社」の場合 → 出社日数が**2日以下**の企業のみ選定
   - **クエリの数値を超える企業は絶対に選ばない**

3. **数値が近いだけでは選ばない:**
   - 「週1出社」と「週3出社」は言葉は似ているが、数値的には3倍の差がある
   - **文脈的な類似度ではなく、数値的な条件を優先**すること

---

## 🔧 技術的な制約

- 新しいPythonスクリプトは作成せず、既存ツール (Read/Write/Bash) を直接使用
- データはndjson形式 (1行1JSON) なので、適切にパース
- 結果ディレクトリ (output/) が存在しない場合は作成
