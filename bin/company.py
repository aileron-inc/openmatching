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
    
    # OpenCode 実行
    prompt = f"""「{query}」に合う企業を{count}社探してください。

重要: 
- このディレクトリ（workspace/）内のファイルのみを使用すること
- companies.ndjson から企業データを読み込む
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
