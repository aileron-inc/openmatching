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
        print("Usage: uv run job.py <SEARCH_QUERY> [COUNT] [--continue <session_id>]")
        print('Example: uv run job.py "Pythonエンジニア" 10')
        print(
            'Example: uv run job.py "Pythonエンジニア" 10 --continue 01ARZ3NDEKTSV4RRFFQ69G5FAV'
        )
        sys.exit(1)

    query = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10

    # セッションIDの解析
    ulid = None
    continue_mode = False
    for i, arg in enumerate(sys.argv):
        if arg == "--continue" and i + 1 < len(sys.argv):
            ulid = sys.argv[i + 1]
            continue_mode = True
            break

    project_root = Path(__file__).parent.parent
    workspace_dir = project_root / "workspace"

    if not ulid:
        # 新規セッション：ULID生成
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

    # 環境変数からモデルを設定（デフォルト: opencode/grok-code）
    opencode_model = os.getenv("OPENCODE_MODEL", "opencode/grok-code")
    opencode_cmd.extend(["--model", opencode_model])
    print(f"🤖 OpenCode Model: {opencode_model}")

    # Salesforce URL を環境変数から取得
    salesforce_base_url = os.getenv(
        "SALESFORCE_BASE_URL", "https://your-org.lightning.force.com"
    )

    # OpenCode 実行
    if continue_mode:
        prompt = f"""前の検索結果を続けて処理してください。検索クエリ: {query}, セッションID: {ulid}

1. output/{ulid}/choices.json を読んでユーザーの選択を確認
2. 条件に従って filtered_jobs.ndjson をフィルタリング
3. フィルタリング後が{count}件以下ならレポート作成（jobs_summary.md, jobs.csv）
4. それでも{count * 5}件超なら、再度 choices.json に選択肢を保存して終了
"""
    else:
        prompt = f"""「{query}」に合う求人を検索してください。検索クエリ: {query}, セッションID: {ulid}

Step 1: キーワードパターン生成（類義語・関連技術含める）
Step 2: ripgrepで件数チェック → wc -l
Step 3: 件数が{count}件以下ならすぐにレポート作成、{count * 5}件超なら choices.json に選択肢保存して終了

choices.json の形式は：query, total_count, suggestions（id, text, type, pattern/count）, message

詳細手順:
- Step 1: キーワードパターン生成
- Step 2: ripgrepで件数チェック
- Step 3: 件数{count}件以下ならレポート作成（jobs_summary.md, jobs.csv）、{count * 5}件超ならchoices.json保存して終了
- Step 4: 続きモードならchoices.json読んで条件に従ってフィルタリング

作業ディレクトリは output/{ulid}/ 内のみ。
"""

    opencode_cmd.append(prompt)

    result = subprocess.run(opencode_cmd, cwd=workspace_dir, check=False)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
