#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-ulid", "typing-extensions"]
# ///
"""
Job Search Interface

キーワードに合う求人を検索する。

Usage:
    uv run job.py "Pythonエンジニア" 10
    uv run job.py "フルリモート"
"""

import os
import sys
import subprocess
from pathlib import Path
from ulid import ULID


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: uv run job.py <SEARCH_QUERY> [COUNT]")
        print('Example: uv run job.py "Pythonエンジニア" 10')
        print('Example: uv run job.py "フルリモート"')
        sys.exit(1)

    query = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    project_root = Path(__file__).parent.parent
    workspace_dir = project_root / "workspace"

    # ULID生成
    ulid = str(ULID())
    work_dir = workspace_dir / "output" / ulid
    chunks_dir = work_dir / "chunks"

    # ディレクトリ作成
    chunks_dir.mkdir(parents=True, exist_ok=True)

    print(f"📍 Working directory: {workspace_dir}")
    print(f"🆔 Process ID (ULID): {ulid}")
    print(f"🔍 Search Query: {query}")
    print(f"📊 Count: {count}件")
    print()

    # OpenCode設定
    opencode_cmd = ["opencode", "run"]

    # 環境変数からモデルを設定（デフォルト: xai/grok-code-fast）
    opencode_model = os.getenv("OPENCODE_MODEL", "xai/grok-code-fast")
    opencode_cmd.extend(["--model", opencode_model])
    print(f"🤖 OpenCode Model: {opencode_model}")

    # Salesforce URL を環境変数から取得
    salesforce_base_url = os.getenv(
        "SALESFORCE_BASE_URL", "https://your-org.lightning.force.com"
    )

    # OpenCode 実行
    prompt = f"""「{query}」に合う求人を{count}件探してください。

## 🔍 2段階処理戦略

このタスクは大きなファイル（jobs.ndjson: 65MB, 6500件）を効率的に処理するため、2段階で行います：

### Step 1: Bashで粗フィルタリング（高速・機械的）

まず、検索クエリに関連しそうなキーワードでgrepフィルタリングを行い、候補を数百件程度に絞り込みます。

```bash
# 検索クエリ「{query}」から関連キーワードを抽出してgrepパターンを作成
# 例: "Pythonエンジニア" → "python|Python|engineer|エンジニア" など
# 例: "リモートワーク" → "リモート|remote|在宅|フルリモート|出社不要" など
# 例: "SaaS スタートアップ" → "SaaS|saas|スタートアップ|startup|ベンチャー" など

# 類義語・関連語も含めて幅広くフィルタリング（後でAIが精密ランキングするので多めに取る）
grep -iE "関連キーワード1|関連キーワード2|類義語1|類義語2|..." jobs.ndjson > output/{ulid}/chunks/filtered_jobs.ndjson

# 件数確認
wc -l output/{ulid}/chunks/filtered_jobs.ndjson
```

**重要:** 
- 元の `jobs.ndjson` は**絶対に直接読み込まない**こと
- フィルタリング後は**必ず500件以下に制限**してください（例: `head -500`）
- 500件超の場合、処理がタイムアウトする可能性があります

### Step 2: OpenCodeで精密ランキング（AI判断・文脈理解）

`filtered_jobs.ndjson` (500件以下) をReadツールで読み込み、以下の観点で評価・ランキングします：

1. **検索意図との適合度**: 「{query}」が求める本質的なニーズに合っているか
2. **総合的な魅力度**: 年収・勤務地・リモート可否・企業の成長性など
3. **文脈理解**: キーワードだけでなく、職務内容全体を見て判断

**必ず以下の2ファイルを作成してください:**
1. `output/{ulid}/jobs_summary.md` - 詳細レポート（Slack Canvas表示用）
2. `output/{ulid}/jobs.csv` - データリスト（スプレッドシート用）

上位{count}件を選出して、最終レポートとCSVを作成してください。

## 出力形式の要件

### サマリーファイル（jobs_summary.md）
このサマリーは **Slack Canvas で最終成果物として表示される** ため、読みやすく詳細なレポート形式で作成してください。

**必須セクション:**

1. **検索概要**
   - 検索クエリ: {query}
   - 検索日時
   - 処理ID (ULID): {ulid}
   - 該当求人総数
   - 処理時間

2. **求人一覧**（各求人について以下を記載）
   
   ### [企業名] - [職種]（求人ID: J-XXXXXXXXXX）
   
   **基本情報**
   - 勤務地: [勤務地]
   - 雇用形態: [正社員/契約社員等]
   - 想定年収: XXX万円〜XXX万円
   - リモート: [可/不可/週X日等]
   - 最終更新日: YYYY-MM-DD
   
   **なぜこの求人が該当するのか**
   この求人は[具体的な職種・業務内容]であり、検索クエリ「{query}」と高い親和性があります。
   特に[特筆すべきポイント]は、検索条件と完全に一致しています。
   [その他の魅力・特徴]も考慮すると、該当する候補者にとって魅力的な案件と判断しました。
   
   **マッチポイント**
   ✅ [技術・スキル要件のマッチ点]
   ✅ [業界・業務内容のマッチ点]
   ✅ [働き方・条件のマッチ点]
   ✅ [その他のプラス要素]
   
   **求められるスキル・経験**
   - [必須スキル1]
   - [必須スキル2]
   - [歓迎スキル1]
   
   **詳細情報**
   - Salesforce: [求人を開く]({salesforce_base_url}/...)
   
   ---

3. **統計情報**
   - 想定年収の分布（〜500万: X件, 500-700万: Y件, 700万〜: Z件）
   - リモート可の割合
   - 勤務地の分布

**重要な原則:**
- 各求人について「なぜ検索クエリに合うのか」を具体的に説明すること
- 検索条件と求人内容の対応関係を明確に示すこと
- 抽象的な表現ではなく、具体的な事実に基づいて記述すること
- 読み手が即座に理解できる文章にすること

## 出力先

- サマリー: `output/{ulid}/jobs_summary.md`
- CSV: `output/{ulid}/jobs.csv`
- 中間ファイル: `output/{ulid}/chunks/` (フィルタリング結果、チャンクファイル等)

## 📋 処理上の重要な注意点

**禁止事項:**
- ❌ `jobs.ndjson` (65MB) を直接Readツールで読み込むこと → タイムアウトします
- ❌ 500件を超えるfiltered_jobs.ndjsonを読み込むこと → タイムアウトリスクあり
- ❌ Taskツールで並列処理 → 今回は不要（filtered_jobs.ndjsonは十分小さい）
- ❌ 親ディレクトリ（../）へのアクセス

**必須事項:**
- ✅ Step 1: Bashでgrepフィルタリング → 500件以下に制限
- ✅ Step 2: `output/{ulid}/chunks/filtered_jobs.ndjson` をReadツールで読み込む
- ✅ Step 3: 上位{count}件を選出して評価
- ✅ **Step 4: 必ず最終成果物を作成** → `output/{ulid}/jobs_summary.md` と `output/{ulid}/jobs.csv`
- ✅ 作業ディレクトリ: `workspace/` 内のみ

**⚠️ 重要: 最終ファイルを必ず作成してください**
処理が完了したら、必ずWriteツールで以下の2ファイルを作成すること：
1. `output/{ulid}/jobs_summary.md`
2. `output/{ulid}/jobs.csv`

これらのファイルがないと、Slackに結果を投稿できません。
"""

    opencode_cmd.append(prompt)

    result = subprocess.run(opencode_cmd, cwd=workspace_dir, check=False)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
