#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""
Company Search Interface

条件に合う企業を検索する。

Usage:
    uv run company.py "SaaS系スタートアップ" 10
    uv run company.py "週1出社" 20
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: uv run company.py <SEARCH_QUERY> [COUNT]")
        print("Example: uv run company.py \"SaaS系スタートアップ\" 10")
        print("Example: uv run company.py \"週1出社\"")
        sys.exit(1)
    
    query = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    project_root = Path(__file__).parent.parent
    workspace_dir = project_root / 'workspace'
    
    # workspace ディレクトリに移動
    print(f"📍 Working directory: {workspace_dir}")
    print(f"🔍 Search Query: {query}")
    print(f"📊 Count: {count}社")
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
    prompt = f"""「{query}」に合う企業を{count}社探してください。

## 出力形式の要件

### サマリーファイル（companies_*_summary.md）について
このサマリーは **Slack Canvas で最終成果物として表示される** ため、読みやすく詳細なレポート形式で作成してください。

**必須セクション:**

1. **検索概要**
   - 検索クエリ
   - 検索日時
   - 該当企業総数
   - 処理時間

2. **企業一覧**（各企業について以下を記載）
   
   ### [企業名]
   
   **基本情報**
   - 業種: [業種]
   - 従業員数: XX名
   - 所在地: [住所]
   - 最終更新日: YYYY-MM-DD
   
   **なぜこの企業が該当するのか**
   この企業は[具体的な事業内容・特徴]であり、検索クエリ「{query}」と高い親和性があります。
   特に[特筆すべきポイント]は、検索条件と完全に一致しています。
   [その他の魅力・特徴]も考慮すると、該当する候補者にとって魅力的な企業と判断しました。
   
   **マッチポイント**
   ✅ [事業内容のマッチ点]
   ✅ [企業文化・働き方のマッチ点]
   ✅ [成長性・安定性のマッチ点]
   ✅ [その他のプラス要素]
   
   **詳細情報**
   - Salesforce: [企業を開く]({salesforce_base_url}/...)
   
   ---

3. **統計情報**
   - 業種分布
   - 従業員規模分布
   - 所在地分布

**重要な原則:**
- 各企業について「なぜ検索クエリに合うのか」を具体的に説明すること
- 検索条件と企業情報の対応関係を明確に示すこと
- 抽象的な表現ではなく、具体的な事実に基づいて記述すること
- 読み手が即座に理解できる文章にすること

## 技術的制約

- このディレクトリ（workspace/）内のファイルのみを使用すること
- companies.ndjson から企業データを読み込む
  - **重要**: ファイルが大きい場合は、Bash コマンドで最初の500-1000行をサンプリングしてから処理すること
  - 例: `head -n 1000 companies.ndjson > companies_sample.ndjson` を実行してから読み込む
  - または、Python でストリーミング処理（1行ずつ読み込み）を行う
- 結果は output/ ディレクトリに保存する
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
