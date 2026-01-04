#!/usr/bin/env python3
"""
Simple GitHub File Updater

GitHub APIでファイルを取得して上書きする
"""

import os
import sys
import base64
import subprocess
from pathlib import Path
import requests


def update_from_github(repo_owner="aileron-inc", repo_name="openmatching", branch="main"):
    """GitHubからファイルを取得して更新"""
    
    project_root = Path(__file__).parent.parent
    
    # 更新対象ファイル
    files_to_update = [
        "bin/bot.py",
        "bin/job.py",
        "bin/company.py",
        "bin/download.py",
        "workspace/AGENTS.md"
    ]
    
    # GitHub Token（環境変数から取得、なくてもpublicリポジトリならOK）
    token = os.getenv('GITHUB_TOKEN', '')
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    updated_files = []
    
    for file_path in files_to_update:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
        
        print(f"📥 {file_path} をチェック中...")
        
        try:
            response = requests.get(url, headers=headers, params={'ref': branch})
            response.raise_for_status()
            
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            
            local_file = project_root / file_path
            
            # ファイルが存在し、内容が同じならスキップ
            if local_file.exists():
                current_content = local_file.read_text(encoding='utf-8')
                if current_content == content:
                    print(f"  ✓ 変更なし")
                    continue
            
            # ディレクトリ作成
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル書き込み
            local_file.write_text(content, encoding='utf-8')
            print(f"  ✅ 更新完了")
            updated_files.append(file_path)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"  ⚠️ ファイルが見つかりません（スキップ）")
            else:
                print(f"  ❌ エラー: {e}")
        except Exception as e:
            print(f"  ❌ エラー: {e}")
    
    return updated_files


def main():
    """メイン処理"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔄 GitHub からファイルを更新")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    
    updated_files = update_from_github()
    
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if updated_files:
        print(f"✅ {len(updated_files)}個のファイルを更新しました")
        for f in updated_files:
            print(f"  - {f}")
        print()
        print("ℹ️  bot.py を再起動してください:")
        print("   sudo systemctl restart slack-matching-bot")
    else:
        print("✅ すべて最新です")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == '__main__':
    main()
