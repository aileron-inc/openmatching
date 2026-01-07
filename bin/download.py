#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests", "simple-salesforce", "pandas", "python-dotenv"]
# ///
"""
Data Download & Conversion Pipeline

Salesforce からCSVをダウンロードし、NDJSON形式に変換して workspace/ に配置する。

Usage:
    uv run download.py
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
import requests
from simple_salesforce import Salesforce
from urllib.parse import urlparse
import pandas as pd
from dotenv import load_dotenv


def get_report_ids() -> dict:
    """環境変数からレポートIDを取得"""
    report_ids_str = os.getenv("SALESFORCE_REPORT_IDS")

    if not report_ids_str:
        print("❌ Error: SALESFORCE_REPORT_IDS 環境変数が設定されていません")
        print("   .env ファイルに以下の形式で追加してください:")
        print(
            "   SALESFORCE_REPORT_IDS='レポートID1:ファイル名1.csv,レポートID2:ファイル名2.csv,...'"
        )
        sys.exit(1)

    try:
        # カンマ区切りでパース: "ID1:file1.csv,ID2:file2.csv,..."
        report_ids = {}
        for pair in report_ids_str.split(","):
            if ":" in pair:
                report_id, filename = pair.split(":", 1)
                report_ids[report_id.strip()] = filename.strip()

        if not report_ids:
            print("❌ Error: SALESFORCE_REPORT_IDS が空です")
            print("   .env ファイルで正しく設定されているか確認してください")
            sys.exit(1)

        return report_ids
    except Exception as e:
        print(f"❌ Error: レポートIDのパースに失敗しました: {e}")
        print("   .env ファイルのフォーマットを確認してください")
        print("   正しい形式: SALESFORCE_REPORT_IDS='ID1:file1.csv,ID2:file2.csv'")
        sys.exit(1)


def parse_yaml_like_credentials(creds_str: str) -> dict:
    """YAML風の認証情報文字列をパース"""
    # {key: value, ...} 形式を {"key": "value", ...} 形式に変換
    # クォートなしのキーと値をクォート付きに変換
    creds_str = creds_str.strip()

    # すでにJSON形式ならそのまま
    if creds_str.startswith('{"'):
        return json.loads(creds_str)

    # YAML風形式の場合、手動でパース
    result = {}
    # {key: value, key2: value2} を抽出
    content = creds_str.strip("{}")
    pairs = content.split(",")

    for pair in pairs:
        if ":" in pair:
            key, value = pair.split(":", 1)
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            result[key] = value

    return result


def get_credentials() -> dict:
    """環境変数から認証情報を取得"""
    creds_str = os.getenv("SALESFORCE_CREDENTIALS")
    if not creds_str:
        print("❌ Error: SALESFORCE_CREDENTIALS 環境変数が設定されていません")
        sys.exit(1)

    try:
        return parse_yaml_like_credentials(creds_str)
    except Exception as e:
        print(f"❌ Error: 認証情報のパースに失敗しました: {e}")
        sys.exit(1)


def download_report(
    session_id: str, instance_url: str, report_id: str, output_path: Path
) -> bool:
    """レポートをダウンロード"""

    # エクスポートURL（Classic UI方式）
    export_url = f"{instance_url}/{report_id}?export=1&enc=UTF-8&xf=csv&isdtp=p1"

    # リクエスト準備
    session = requests.Session()
    parsed_url = urlparse(instance_url)
    session.cookies.set("sid", session_id, domain=parsed_url.hostname)

    headers = {
        "Authorization": f"Bearer {session_id}",
        "Accept": "text/csv",
        "User-Agent": "Mozilla/5.0 (compatible; SalesforceReportExporter/1.0)",
    }

    # ダウンロード実行
    print(f"  📡 {output_path.name} をダウンロード中...")
    response = session.get(export_url, headers=headers, timeout=60)

    if response.status_code != 200:
        print(f"  ❌ エラー: HTTP {response.status_code}")
        return False

    # CSV保存
    output_path.write_text(response.text, encoding="utf-8")
    print(f"  ✅ 保存完了: {output_path.name}")
    return True


def filter_candidates(
    df, recent_interview_days=60, min_survey_year=2024, valid_ranks=["S", "A", "B"]
):
    """求職者データをフィルタリング"""
    original_count = len(df)
    print(f"🔍 求職者データをフィルタリング中... (元: {original_count}件)")

    # カラム名の正規化（前後の空白・BOM除去）
    df.columns = df.columns.str.strip()

    # ランクフィルタ
    rank_col = "個人ユーザー/企業: 登録時ランク"
    if rank_col in df.columns:
        before = len(df)
        df = df[df[rank_col].isin(valid_ranks)].copy()
        print(
            f"  ランクフィルタ ({', '.join(valid_ranks)}): {len(df)}件 ({before - len(df)}件除外)"
        )

    # アンケート回答日フィルタ
    survey_col = "アンケート回答日時"
    if survey_col in df.columns:
        min_survey_date = datetime(min_survey_year, 1, 1)
        df.loc[:, survey_col] = pd.to_datetime(df[survey_col], errors="coerce")
        before = len(df)
        df = df[df[survey_col] >= min_survey_date].copy()
        print(
            f"  アンケート日フィルタ ({min_survey_year}年以降): {len(df)}件 ({before - len(df)}件除外)"
        )

    # 初回面談日 OR 選考中フィルタ
    interview_col = "個人ユーザー/企業: 初回面談日時"
    status_col = "選考ステータス"

    if interview_col in df.columns:
        recent_date = datetime.now() - timedelta(days=recent_interview_days)
        df.loc[:, interview_col] = pd.to_datetime(df[interview_col], errors="coerce")

        active_statuses = [
            "書類選考中",
            "一次面接中",
            "二次面接中",
            "最終面接中",
            "オファー面談中",
        ]
        recent_interview = df[interview_col] >= recent_date

        if status_col in df.columns:
            active_selection = df[status_col].isin(active_statuses)
            before = len(df)
            df = df[recent_interview | active_selection].copy()
            print(
                f"  面談日({recent_interview_days}日以内) OR 選考中: {len(df)}件 ({before - len(df)}件除外)"
            )

    # 最終更新日フィルタ
    update_col = "最終更新日"
    if update_col in df.columns:
        last_year = datetime.now() - timedelta(days=365)
        df.loc[:, update_col] = pd.to_datetime(df[update_col], errors="coerce")
        before = len(df)
        df = df[df[update_col] >= last_year].copy()
        print(f"  最終更新日(365日以内): {len(df)}件 ({before - len(df)}件除外)")

    print(f"✅ フィルタリング済み: {original_count}件 → {len(df)}件\n")
    return df


def filter_jobs(df, job_status="アクティブ"):
    """求人データをフィルタリング"""
    original_count = len(df)
    print(f"🔍 求人データをフィルタリング中... (元: {original_count}件)")

    # カラム名の正規化
    df.columns = df.columns.str.strip()

    # 求人状態フィルタ
    status_col = None
    if "求人状態" in df.columns:
        status_col = "求人状態"
    elif "求人票 求人状態" in df.columns:
        status_col = "求人票 求人状態"

    if status_col:
        before = len(df)
        df = df[df[status_col] == job_status]
        print(
            f"  求人状態フィルタ ({job_status}): {len(df)}件 ({before - len(df)}件除外)"
        )

    print(f"✅ フィルタリング済み: {original_count}件 → {len(df)}件\n")
    return df


def to_ndjson(df, output_path):
    """DataFrameをNDJSON形式で保存"""
    print(f"💾 NDJSON保存中: {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            record = {}
            for key, value in row.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    record[key] = str(value)
                else:
                    record[key] = value

            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✅ 保存完了: {len(df)}件\n")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent
    tmp_dir = project_root / "tmp"
    workspace_dir = project_root / "workspace"

    # .env ファイル読み込み (.envがあれば読み込む。既存の環境変数は上書きしない)
    load_dotenv(dotenv_path=project_root / ".env", override=False)

    # ディレクトリ作成
    tmp_dir.mkdir(exist_ok=True)
    workspace_dir.mkdir(exist_ok=True)

    # 環境変数から設定を読み込み
    recent_interview_days = int(os.environ.get("RECENT_INTERVIEW_DAYS", "60"))
    min_survey_year = int(os.environ.get("MIN_SURVEY_YEAR", "2024"))
    valid_ranks = os.environ.get("VALID_RANKS", "S,A,B").split(",")
    job_status = os.environ.get("JOB_STATUS", "アクティブ")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📥 Data Download & Conversion Pipeline")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # Step 1: Salesforce ダウンロード
    print("🔐 Step 1: Salesforce に接続中...")
    creds = get_credentials()
    sf = Salesforce(
        username=creds["username"],
        password=creds["password"],
        security_token=creds["security_token"],
        domain=creds.get("domain", "login"),
    )

    session_id = sf.session_id
    instance_url = sf.sf_instance

    if not instance_url.startswith("http"):
        instance_url = f"https://{instance_url}"

    print(f"✅ 接続成功: {instance_url}")
    print()

    # レポートID取得
    report_ids = get_report_ids()

    print(f"📥 Step 2: レポートダウンロード開始 ({len(report_ids)}件)")
    print()

    success_count = 0
    for report_id, filename in report_ids.items():
        output_path = tmp_dir / filename
        if download_report(session_id, instance_url, report_id, output_path):
            success_count += 1

    print()
    if success_count < len(report_ids):
        print(f"⚠️ ダウンロード失敗: {success_count}/{len(report_ids)}件")
        sys.exit(1)

    print(f"✅ ダウンロード完了: {success_count}/{len(report_ids)}件")
    print()

    # Step 3: NDJSON 変換
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔄 Step 3: NDJSON 変換")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"📋 フィルタリング設定:")
    print(f"  - 初回面談日: {recent_interview_days}日以内")
    print(f"  - アンケート回答: {min_survey_year}年以降")
    print(f"  - 登録時ランク: {', '.join(valid_ranks)}")
    print(f"  - 求人状態: {job_status}")
    print()

    # 求職者処理
    candidates_csv = tmp_dir / "求職者.csv"
    print("📖 求職者RAWデータを読み込み中...")
    candidates_df = pd.read_csv(candidates_csv, encoding="utf-8-sig")
    candidates_df = filter_candidates(
        candidates_df,
        recent_interview_days=recent_interview_days,
        min_survey_year=min_survey_year,
        valid_ranks=valid_ranks,
    )
    to_ndjson(candidates_df, workspace_dir / "candidates.ndjson")

    # 求人処理
    jobs_csv = tmp_dir / "求人票.csv"
    print("📖 求人RAWデータを読み込み中...")
    jobs_df = pd.read_csv(jobs_csv, encoding="utf-8-sig")
    jobs_df = filter_jobs(jobs_df, job_status=job_status)
    to_ndjson(jobs_df, workspace_dir / "jobs.ndjson")

    # 企業処理（フィルタリングなし）
    companies_csv = tmp_dir / "企業.csv"
    print("📖 企業RAWデータを読み込み中...")
    companies_df = pd.read_csv(companies_csv, encoding="utf-8-sig")
    companies_df.columns = companies_df.columns.str.strip()
    print(f"✅ 読み込み完了: {len(companies_df)}件")
    print()
    to_ndjson(companies_df, workspace_dir / "companies.ndjson")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ 全て完了！")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("📂 出力先:")
    print(f"  - {workspace_dir / 'candidates.ndjson'} ({len(candidates_df)}件)")
    print(f"  - {workspace_dir / 'jobs.ndjson'} ({len(jobs_df)}件)")
    print(f"  - {workspace_dir / 'companies.ndjson'} ({len(companies_df)}件)")


if __name__ == "__main__":
    main()
