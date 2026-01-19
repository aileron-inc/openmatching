#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-dotenv"]
# ///
"""
OpenCode Models Utility

利用可能なAIモデルを一覧表示する。

Usage:
    uv run bin/models.py
    uv run bin/models.py --provider opencode
    uv run bin/models.py --verbose
    uv run bin/models.py --free
"""

import subprocess
import sys
import re
from pathlib import Path


def list_models(provider=None, verbose=False, free_only=False):
    """利用可能なモデルを一覧表示"""
    cmd = ["opencode", "models"]

    if provider:
        cmd.append(provider)

    if verbose:
        cmd.append("--verbose")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"❌ エラー: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        if free_only:
            filter_and_display_free_models(result.stdout)
        elif verbose:
            print(result.stdout)
        else:
            parse_and_display_models(result.stdout)

    except subprocess.TimeoutExpired:
        print("❌ タイムアウト（30秒超過）", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        sys.exit(1)


def parse_and_display_models(output):
    """モデル出力をパースして表示"""
    lines = output.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("="):
            continue
        print(f"  {line}")


def filter_and_display_free_models(output):
    """無料モデルのみを表示"""
    lines = output.strip().split("\n")

    print("🆓 無料モデル（APIキー不要）:")

    found = False
    for line in lines:
        line = line.strip()
        if "free" in line.lower() and line.startswith("opencode/"):
            found = True
            print(f"  ✅ {line}")

    if not found:
        print("  見つかりませんでした")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="利用可能なAIモデルを一覧表示")
    parser.add_argument(
        "--provider", help="プロバイダでフィルタ（例: opencode, anthropic）"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="詳細情報を表示（コストなど）"
    )
    parser.add_argument("--free", "-f", action="store_true", help="無料モデルのみ表示")
    args = parser.parse_args()

    print("=" * 60)
    print("🤖 利用可能なAIモデル")
    print("=" * 60)
    print()

    list_models(provider=args.provider, verbose=args.verbose, free_only=args.free)

    print()
    print("=" * 60)
    print()
    print("💡 使用方法:")
    print("   uv run bin/models.py              # すべてのモデル")
    print("   uv run bin/models.py --verbose    # 詳細情報付き")
    print("   uv run bin/models.py --free       # 無料モデルのみ")
    print("   uv run bin/models.py --provider opencode  # プロバイダでフィルタ")
    print()
    print("📝 .envファイルでモデル指定:")
    print("   OPENCODE_MODEL=opencode/glm-4.7-free")
    print("   OPENCODE_MODEL=claude-3-5-sonnet-20241022")


if __name__ == "__main__":
    main()
