#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///
"""
Environment Check Utility

環境変数とツールの動作確認を行う。

Usage:
    uv run bin/env.py
    uv run bin/env.py --test-opencode
"""

import os
import sys
import subprocess
from pathlib import Path


def check_env_vars():
    """環境変数チェック"""
    results = []
    
    required_vars = {
        'SALESFORCE_CREDENTIALS': 'Salesforce認証',
        'SALESFORCE_BASE_URL': 'Salesforce URL',
        'SLACK_BOT_TOKEN': 'Slackボット',
        'SLACK_APP_TOKEN': 'Slack App',
        'SLACK_CH': '通知チャンネル',
    }
    
    for var_name, var_desc in required_vars.items():
        value = os.getenv(var_name)
        if value:
            results.append({
                'status': 'ok',
                'name': var_name,
                'desc': var_desc,
                'length': len(value)
            })
        else:
            results.append({
                'status': 'missing',
                'name': var_name,
                'desc': var_desc
            })
    
    # OpenCode設定
    opencode_model = os.getenv('OPENCODE_MODEL')
    opencode_api_key = os.getenv('OPENCODE_API_KEY')
    
    results.append({
        'status': 'info',
        'name': 'OPENCODE_MODEL',
        'value': opencode_model or 'デフォルト'
    })
    
    if opencode_api_key:
        results.append({
            'status': 'ok',
            'name': 'OPENCODE_API_KEY',
            'length': len(opencode_api_key)
        })
    else:
        results.append({
            'status': 'info',
            'name': 'OPENCODE_API_KEY',
            'value': '未設定（無料モデル使用）'
        })
    
    return results


def check_tools():
    """ツールの存在確認"""
    results = []
    
    # uv
    try:
        uv_which = subprocess.run(['which', 'uv'], capture_output=True, text=True, timeout=5)
        if uv_which.returncode == 0:
            uv_version = subprocess.run(['uv', '--version'], capture_output=True, text=True, timeout=5)
            results.append({
                'status': 'ok',
                'name': 'uv',
                'version': uv_version.stdout.strip(),
                'path': uv_which.stdout.strip()
            })
        else:
            results.append({'status': 'missing', 'name': 'uv'})
    except Exception as e:
        results.append({'status': 'error', 'name': 'uv', 'error': str(e)})
    
    # opencode
    try:
        oc_which = subprocess.run(['which', 'opencode'], capture_output=True, text=True, timeout=5)
        if oc_which.returncode == 0:
            oc_version = subprocess.run(['opencode', '--version'], capture_output=True, text=True, timeout=5)
            results.append({
                'status': 'ok',
                'name': 'opencode',
                'version': oc_version.stdout.strip(),
                'path': oc_which.stdout.strip()
            })
        else:
            results.append({'status': 'missing', 'name': 'opencode'})
    except Exception as e:
        results.append({'status': 'error', 'name': 'opencode', 'error': str(e)})
    
    return results


def test_opencode():
    """OpenCode実行テスト"""
    test_prompt = "1から5までの数字をカンマ区切りで出力してください。他の説明は不要です。"
    
    try:
        project_dir = Path(__file__).parent.parent.resolve()
        
        # GLM 4.7 (無償モデル) でテスト
        result = subprocess.run(
            ['opencode', 'run', '--model', 'opencode/glm-4.7-free', test_prompt],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                'status': 'ok',
                'model': 'opencode/glm-4.7-free',
                'prompt': test_prompt,
                'output': result.stdout.strip()
            }
        else:
            return {
                'status': 'error',
                'error': result.stderr.strip() or result.stdout.strip()
            }
    
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='環境チェックツール')
    parser.add_argument('--test-opencode', action='store_true', help='OpenCode実行テスト')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔍 環境チェック")
    print("=" * 60)
    print()
    
    # 環境変数
    print("📋 環境変数:")
    env_results = check_env_vars()
    for r in env_results:
        if r['status'] == 'ok':
            print(f"  ✅ {r['desc']}: 設定済み ({r['length']}文字)")
        elif r['status'] == 'missing':
            print(f"  ❌ {r['desc']}: 未設定")
        elif r['status'] == 'info':
            print(f"  ℹ️  {r['name']}: {r.get('value', '設定済み')}")
    
    print()
    
    # ツール
    print("🔧 ツール:")
    tool_results = check_tools()
    for r in tool_results:
        if r['status'] == 'ok':
            print(f"  ✅ {r['name']}: {r['version']}")
            print(f"     パス: {r['path']}")
        elif r['status'] == 'missing':
            print(f"  ❌ {r['name']}: 未インストール")
        elif r['status'] == 'error':
            print(f"  ⚠️  {r['name']}: エラー ({r['error']})")
    
    print()
    
    # OpenCodeテスト
    if args.test_opencode:
        print("🧪 OpenCode実行テスト:")
        test_result = test_opencode()
        
        if test_result['status'] == 'ok':
            print(f"  ✅ 成功")
            print(f"     モデル: {test_result['model']}")
            print(f"     プロンプト: {test_result['prompt']}")
            print(f"     結果: {test_result['output'][:100]}")
        elif test_result['status'] == 'timeout':
            print(f"  ⏱️  タイムアウト（30秒超過）")
        else:
            print(f"  ❌ エラー")
            print(f"     {test_result['error'][:200]}")
        
        print()
    
    print("=" * 60)


if __name__ == '__main__':
    main()
