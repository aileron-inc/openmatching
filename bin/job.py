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
        print("Example: uv run job.py \"Pythonエンジニア\" 10")
        print("Example: uv run job.py \"フルリモート\"")
        sys.exit(1)
    
    query = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    project_root = Path(__file__).parent.parent
    workspace_dir = project_root / 'workspace'
    
    # ULID生成
    ulid = str(ULID())
    work_dir = workspace_dir / 'output' / ulid
    chunks_dir = work_dir / 'chunks'
    
    # ディレクトリ作成
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📍 Working directory: {workspace_dir}")
    print(f"🆔 Process ID (ULID): {ulid}")
    print(f"🔍 Search Query: {query}")
    print(f"📊 Count: {count}件")
    print()
    
    # OpenCode設定
    opencode_cmd = ['opencode', 'run']
    
    # 環境変数からモデルを設定
    opencode_model = os.getenv('OPENCODE_MODEL')
    if opencode_model:
        opencode_cmd.extend(['--model', opencode_model])
        print(f"🤖 OpenCode Model: {opencode_model}")
    
    # Salesforce URL を環境変数から取得
    salesforce_base_url = os.getenv('SALESFORCE_BASE_URL', 'https://your-org.lightning.force.com')
    
    # OpenCode 実行
    prompt = f"""「{query}」に合う求人を{count}件探してください。

## 処理の流れ

このタスクは大きなファイル（jobs.ndjson: 65MB, 6500件）を扱うため、以下の手順で分割処理してください：

### Step 1: キーワードフィルタリング
検索クエリに関連しそうなキーワードを使って、jobs.ndjsonから候補を絞り込みます。

```bash
# 検索クエリから関連キーワードを抽出してgrepで絞り込む
# 例: "Pythonエンジニア 六本木" なら "python\|engineer\|六本木\|エンジニア" など
grep -iE "関連キーワード1|関連キーワード2|..." jobs.ndjson > output/{ulid}/chunks/filtered_jobs.ndjson
```

**重要:** 元のjobs.ndjsonは直接読み込まないこと。必ずこのフィルタリングを最初に行ってください。

### Step 2: ファイル分割
フィルタリング済みファイルを3-4個のチャンクに分割します。

```bash
cd output/{ulid}/chunks
# filtered_jobs.ndjsonを500行ずつ分割
split -l 500 filtered_jobs.ndjson chunk_
```

これで chunk_aa, chunk_ab, chunk_ac... のようなファイルができます。

### Step 3: 並列検索（Taskツールを使用）
各チャンクを別々のサブエージェント（Task）で検索します。

```
Task 1: chunk_aa を検索してマッチする求人トップ5を返す
Task 2: chunk_ab を検索してマッチする求人トップ5を返す  
Task 3: chunk_ac を検索してマッチする求人トップ5を返す
Task 4: chunk_ad を検索してマッチする求人トップ5を返す (もしあれば)
```

各Taskには以下のプロンプトを渡してください：
「output/{ulid}/chunks/chunk_XX を読み込んで、検索クエリ「{query}」に合う求人トップ5を選んでください。結果はJSON配列で返してください。」

### Step 4: 結果の統合
各Taskから返ってきた候補（最大20件）から、最終的なトップ{count}件を選出します。

### Step 5: 最終レポート作成
選ばれたトップ{count}件について、以下の形式でレポートを作成してください。

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

## 技術的制約

- このディレクトリ（workspace/）内のファイルのみを使用すること
- 作業ディレクトリ: output/{ulid}/
- 中間ファイル保存先: output/{ulid}/chunks/
- 元のjobs.ndjsonは直接読み込まないこと（必ずフィルタリング経由）
- 親ディレクトリ（../）のファイルにはアクセスしない
"""
    
    opencode_cmd.append(prompt)
    
    result = subprocess.run(
        opencode_cmd,
        cwd=workspace_dir,
        check=False
    )
    
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
