#!/usr/bin/env -S uv run
# /// script
# dependencies = ["python-ulid", "typing-extensions"]
# ///
"""
Candidate Matching Interface

求人IDに対して候補者をマッチングする。

Usage:
    uv run candidate.py J-0000023845
    uv run candidate.py 23845
"""

import os
import sys
import subprocess
from pathlib import Path
from ulid import ULID


def normalize_job_id(job_id: str) -> str:
    """求人IDを正規化"""
    # 数字のみの場合は J- プレフィックスを追加
    if job_id.isdigit():
        return f"J-{int(job_id):010d}"
    
    # J- で始まる場合はそのまま
    if job_id.startswith('J-'):
        return job_id
    
    # 006で始まる場合は求人票ID（そのまま）
    if job_id.startswith('006'):
        return job_id
    
    print(f"❌ 不明なID形式: {job_id}")
    print("対応形式: J-0000023845 / 23845 / 006RA00000HzHwb")
    sys.exit(1)


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("Usage: uv run candidate.py <JOB_ID>")
        print("Example: uv run candidate.py J-0000023845")
        print("Example: uv run candidate.py 23845")
        sys.exit(1)
    
    job_id = normalize_job_id(sys.argv[1])
    project_root = Path(__file__).parent.parent
    workspace_dir = project_root / 'workspace'
    
    # ULID生成とディレクトリ作成
    ulid = str(ULID())
    work_dir = workspace_dir / 'output' / ulid
    chunks_dir = work_dir / 'chunks'
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    # workspace ディレクトリに移動
    print(f"📍 Working directory: {workspace_dir}")
    print(f"🎯 Job ID: {job_id}")
    print(f"🆔 Session ULID: {ulid}")
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
    prompt = f"""求人ID「{job_id}」に合う候補者をマッチングしてください。

## 作業ディレクトリとファイル配置

**重要: すべての出力は output/{ulid}/ ディレクトリに保存してください**

- 作業用チャンクファイル: `output/{ulid}/chunks/` に配置
- 最終成果物: `output/{ulid}/matching_summary.md` と `output/{ulid}/matching.csv`

## 出力形式の要件

### サマリーファイル（matching_summary.md）について
このサマリーは **Slack Canvas で最終成果物として表示される** ため、読みやすく詳細なレポート形式で作成してください。

**必須セクション:**

1. **マッチング概要**
   - 求人情報（求人ID、企業名、職種、勤務地など）
   - マッチング日時
   - 候補者総数
   - 処理時間

2. **候補者一覧**（各候補者について以下を記載）
   
   ### [候補者名]（ランク: A+）
   
   **基本情報**
   - 現職: [現在の会社・役職]
   - 年齢: XX歳
   - 希望年収: XXX万円
   - 最終更新日: YYYY-MM-DD
   
   **なぜこの候補者が該当するのか**
   この候補者は[具体的な経験・スキル]を持ち、求人の要件である[要件1、要件2]と高い親和性があります。
   特に[特筆すべきポイント]は、求人が求める[ニーズ]と完全に一致しています。
   [その他の強み・経験]も考慮すると、即戦力として活躍できる可能性が高いと判断しました。
   
   **マッチポイント**
   ✅ [技術スキルのマッチ点]
   ✅ [業界・業務経験のマッチ点]
   ✅ [志向性のマッチ点]
   ✅ [その他のプラス要素]
   
   **懸念点・要確認事項**
   ⚠️ [あれば記載、なければ「特になし」]
   
    **詳細情報**
    - Salesforce: [候補者を開く]({salesforce_base_url}/...)
   
   ---

3. **統計情報**
   - マッチ度分布（A+: X人, A: Y人, B: Z人）
   - 平均年齢、希望年収レンジ
   - 現職の業種分布

**重要な原則:**
- 各候補者について「なぜマッチするのか」を具体的に説明すること
- 求人要件と候補者の経験・スキルの対応関係を明確に示すこと
- 抽象的な表現ではなく、具体的な事実に基づいて記述すること
- 読み手（CAやRAコンサルタント）が即座に理解できる文章にすること

## 🔍 2段階処理戦略

このタスクは大きなファイル（jobs.ndjson: 65MB、candidates.ndjson: 80MB）を効率的に処理するため、2段階で行います：

### Step 1: Bashで事前処理（高速・機械的）

```bash
# 1-1. 対象求人を抽出（求人ID: {job_id}）
grep "{job_id}" jobs.ndjson > output/{ulid}/chunks/target_job.ndjson

# 1-2. 求人の必須スキル・キーワードを抽出してgrepパターンを作成
# 例: 求人が「Python, Django, AWS経験者」を求めているなら
#     → "python|Python|django|Django|aws|AWS|バックエンド|backend" など
# 例: 求人が「営業経験3年以上」を求めているなら
#     → "営業|sales|法人営業|新規開拓" など

# 1-3. 候補者データを粗フィルタリング（数千件→数百件に削減）
grep -iE "関連キーワード1|関連キーワード2|スキル1|スキル2|..." candidates.ndjson > output/{ulid}/chunks/filtered_candidates.ndjson

# 件数確認
wc -l output/{ulid}/chunks/filtered_candidates.ndjson
```

**重要:** 
- `candidates.ndjson` (80MB) は**絶対に直接読み込まない**こと
- フィルタリングは緩めに（後でAIが精密評価するので多めに取る）
- フィルタリング後は**必ず500件以下に制限**してください（例: `head -500`）
- 500件超の場合、処理がタイムアウトする可能性があります

### Step 2: OpenCodeで精密マッチング（AI判断・文脈理解）

1. `target_job.ndjson` を読んで求人要件を理解
2. `filtered_candidates.ndjson` を読んで各候補者を評価
3. 以下の観点でマッチング：
   - 必須スキル・経験の充足度
   - 希望条件（年収・勤務地・働き方）との適合度
   - キャリアの方向性・志向性
   - 即戦力性 vs ポテンシャル

上位10-20名を選出し、ランク付け（A+, A, B）して最終レポートを作成してください。

## 📋 処理上の重要な注意点

**禁止事項:**
- ❌ `jobs.ndjson` (65MB) や `candidates.ndjson` (80MB) を直接Readツールで読み込むこと
- ❌ 500件を超えるfiltered_candidates.ndjsonを読み込むこと → タイムアウトリスクあり
- ❌ Taskツールで並列処理 → 今回は不要（filtered_candidates.ndjsonは十分小さい）
- ❌ 親ディレクトリ（../）へのアクセス

**必須事項:**
- ✅ Step 1: Bashでgrepフィルタリング → 500件以下に制限
- ✅ Step 2: フィルタリング後のファイルをReadツールで読み込む
- ✅ Step 3: マッチング評価・ランク付け
- ✅ **Step 4: 必ず最終成果物を作成** → `output/{ulid}/matching_summary.md` と `output/{ulid}/matching.csv`
- ✅ 作業ディレクトリ: `workspace/` 内のみ

**⚠️ 重要: 最終ファイルを必ず作成してください**
処理が完了したら、必ずWriteツールで以下の2ファイルを作成すること：
1. `output/{ulid}/matching_summary.md`
2. `output/{ulid}/matching.csv`

これらのファイルがないと、Slackに結果を投稿できません。
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
