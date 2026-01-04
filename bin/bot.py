#!/usr/bin/env -S uv run
# /// script
# dependencies = ["slack-bolt", "python-dotenv", "schedule"]
# ///
"""
Slackボット: レコメンド機能（メンション型）

使い方:
  1. .env に SLACK_BOT_TOKEN と SLACK_APP_TOKEN を設定
  2. uv run scripts/bot.py で起動
  3. Slackでボットにメンション:
     @ボット名 job J-0000023845
     @ボット名 company U-12345
"""

import os
import sys
import subprocess
import threading
import queue
import time
import signal
import schedule
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ジョブキュー（1件ずつ順番に処理）
job_queue = queue.Queue()
is_processing = False
processing_lock = threading.Lock()

# 環境変数読み込み
load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# 管理通知先チャンネル
ADMIN_CHANNEL = os.environ.get("SLACK_CH")

# ボット名（起動時に取得）
BOT_NAME = None

def process_company_search(search_query, user_id, say, client, channel_id, thread_ts, count=10):
    """企業探索処理（検索クエリ型）"""
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🔍 企業探索処理開始")
    print(f"{'='*60}")
    print(f"   検索クエリ: {search_query}")
    print(f"   取得件数: {count}社")
    print(f"   依頼者: {user_id}")
    print(f"   スレッド: {thread_ts}")
    print(f"   開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 処理開始メッセージ（スレッド内に投稿）
    status_msg = client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=(
            f"🔍 企業探索を開始しました\n\n"
            f"検索クエリ: `{search_query}`\n"
            f"⏰ 開始時刻: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"処理には数分かかります。このスレッドで進捗をお知らせしますね"
        )
    )
    
    status_ts = status_msg['ts']
    
    try:
        # スクリプトのパスを取得
        project_dir = Path(__file__).parent.parent.resolve()
        company_script = project_dir / "bin" / "company.py"
        
        print(f"📝 スクリプト実行中: {company_script}")
        print(f"{'='*60}")
        print(f"OpenCode 実行ログ:")
        print(f"{'='*60}\n")
        
        # 企業探索実行（標準出力を直接表示）
        result = subprocess.run(
            ["uv", "run", str(company_script), search_query, str(count)],
            cwd=str(project_dir),
            timeout=600,  # 10分でタイムアウト
        )
        
        print(f"\n{'='*60}")
        print(f"OpenCode 実行完了")
        print(f"{'='*60}")
        
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        
        print(f"⏱️  処理時間: {elapsed_str}")
        
        if result.returncode != 0:
            print(f"❌ エラー発生")
            # メッセージ更新
            client.chat_update(
                channel=channel_id,
                ts=status_ts,
                text=(
                    f"❌ 企業探索でエラーが発生しました\n\n"
                    f"検索クエリ: `{search_query}`\n"
                    f"⏱️ 処理時間: {elapsed_str}\n\n"
                    f"申し訳ございません。もう一度お試しください"
                )
            )
            return
        
        # 成功 → 結果ファイルを探してSlackに投稿
        print(f"✅ 企業探索処理完了")
        print(f"📤 Slackへの結果投稿を開始...")
        
        # 最新の結果ファイルを探す
        results_dir = project_dir / "workspace" / "output"
        summary_files = sorted(results_dir.glob("companies_*_summary.md"), reverse=True)
        csv_files = sorted(results_dir.glob("companies_*.csv"), reverse=True)
        
        if summary_files and csv_files:
            latest_summary = summary_files[0]
            latest_csv = csv_files[0]
            
            print(f"📄 サマリーファイル: {latest_summary}")
            print(f"📊 CSVファイル: {latest_csv}")
            
            try:
                # サマリー読み込み
                with open(latest_summary, 'r', encoding='utf-8') as f:
                    summary_text = f.read()
                
                # CSV行数をカウント（ヘッダー除く）
                with open(latest_csv, 'r', encoding='utf-8') as f:
                    company_count = sum(1 for line in f) - 1
                
                canvas_title = f"【企業探索】{search_query} - 結果"
                
                # Canvas作成（スレッド内に投稿）
                print(f"📝 Canvas作成中: {canvas_title}")
                canvas_response = client.canvases_create(
                    title=canvas_title,
                    document_content={
                        "type": "markdown",
                        "markdown": summary_text
                    }
                )
                
                canvas_id = canvas_response['canvas_id']
                print(f"✅ Canvas作成完了: {canvas_id}")
                
                # チャンネルに共有（アクセス権付与）
                client.canvases_access_set(
                    canvas_id=canvas_id,
                    access_level="read",
                    channel_ids=[channel_id]
                )
                
                # Canvas URLを構築
                auth = client.auth_test()
                team_id = auth['team_id']
                workspace_url = auth['url']
                canvas_url = f"{workspace_url}docs/{team_id}/{canvas_id}"
                
                print(f"📊 Canvas URL: {canvas_url}")
                
                # メッセージ更新（完了）
                client.chat_update(
                    channel=channel_id,
                    ts=status_ts,
                    text=(
                        f"✅ 企業探索が完了しました\n\n"
                        f"検索クエリ: `{search_query}`\n"
                        f"見つかった企業: *{company_count}社*\n"
                        f"⏱️ 処理時間: {elapsed_str}\n"
                        f"⏰ 完了時刻: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"📄 詳細はCanvasとCSVをご確認ください\n"
                        f"{canvas_url}"
                    )
                )
                
                # CSVファイルをアップロード（スレッド内）
                print(f"📤 CSVファイルアップロード中...")
                client.files_upload_v2(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    file=str(latest_csv),
                    title=f"企業探索結果 ({company_count}社)",
                    initial_comment=f"📊 全{company_count}社の詳細データ（CSV形式）"
                )
                
                print(f"✅ Slack投稿完了")
                
            except Exception as post_error:
                print(f"⚠️  Slack投稿でエラー: {post_error}")
                import traceback
                traceback.print_exc()
                
                # メッセージ更新（警告）
                client.chat_update(
                    channel=channel_id,
                    ts=status_ts,
                    text=(
                        f"⚠️ 処理は完了しましたが、結果の投稿でエラーが発生しました\n\n"
                        f"検索クエリ: `{search_query}`\n"
                        f"⏱️ 処理時間: {elapsed_str}\n\n"
                        f"以下のファイルを手動でご確認ください:\n"
                        f"サマリー: `{latest_summary.name}`\n"
                        f"CSV: `{latest_csv.name}`"
                    )
                )
        else:
            print(f"⚠️  結果ファイルが見つかりません")
            # メッセージ更新（警告）
            client.chat_update(
                channel=channel_id,
                ts=status_ts,
                text=(
                    f"⚠️ 処理は完了しましたが、結果ファイルが見つかりませんでした\n\n"
                    f"検索クエリ: `{search_query}`\n"
                    f"⏱️ 処理時間: {elapsed_str}\n\n"
                    f"お手数ですが、もう一度お試しください"
                )
            )
        
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        print(f"⏱️  タイムアウト（経過時間: {elapsed_str}）")
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"⏱️ タイムアウト: 処理に10分以上かかっています\n\n"
                f"検索クエリ: `{search_query}`\n"
                f"経過時間: {elapsed_str}\n\n"
                f"申し訳ございません。検索条件を絞ってもう一度お試しください"
            )
        )
    except FileNotFoundError as e:
        elapsed_time = time.time() - start_time
        print(f"❌ ファイルエラー: {e}")
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"❌ システムエラーが発生しました\n\n"
                f"スクリプトが見つかりません\n"
                f"管理者にお問い合わせください"
            )
        )
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 予期しないエラー: {e}")
        
        # 詳細なスタックトレース
        import traceback
        traceback.print_exc()
        
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"❌ 予期しないエラーが発生しました\n\n"
                f"申し訳ございません。もう一度お試しいただくか、\n"
                f"管理者にお問い合わせください"
            )
        )
    finally:
        print(f"{'='*60}\n")

def process_job_recommendation(job_id, user_id, say, client, channel_id, thread_ts):
    """求人レコメンド処理（共通ロジック）"""
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🚀 求人レコメンド処理開始")
    print(f"{'='*60}")
    print(f"   求人ID: {job_id}")
    print(f"   依頼者: {user_id}")
    print(f"   スレッド: {thread_ts}")
    print(f"   開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 処理開始メッセージ（スレッド内に投稿）
    status_msg = client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=(
            f"🚀 求人レコメンドを開始しました\n\n"
            f"求人ID: `{job_id}`\n"
            f"⏰ 開始時刻: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"処理には数分かかります。このスレッドで進捗をお知らせしますね"
        )
    )
    
    status_ts = status_msg['ts']
    
    try:
        # スクリプトのパスを取得（bot.pyと同じディレクトリ）
        project_dir = Path(__file__).parent.parent.resolve()
        job_script = project_dir / "bin" / "job.py"
        
        print(f"📝 スクリプト実行中: {job_script}")
        print(f"{'='*60}")
        print(f"OpenCode 実行ログ:")
        print(f"{'='*60}\n")
        
        # マッチング実行（標準出力を直接表示）
        result = subprocess.run(
            ["uv", "run", str(job_script), job_id],
            cwd=str(project_dir),
            timeout=600,  # 10分でタイムアウト
            # capture_output=False で標準出力をターミナルに表示
        )
        
        print(f"\n{'='*60}")
        print(f"OpenCode 実行完了")
        print(f"{'='*60}")
        
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        
        print(f"⏱️  処理時間: {elapsed_str}")
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "不明なエラー"
            print(f"❌ エラー発生:\n{error_msg}")
            # メッセージ更新
            client.chat_update(
                channel=channel_id,
                ts=status_ts,
                text=(
                    f"❌ 求人レコメンドでエラーが発生しました\n\n"
                    f"求人ID: `{job_id}`\n"
                    f"⏱️ 処理時間: {elapsed_str}\n\n"
                    f"申し訳ございません。求人IDをご確認の上、もう一度お試しください"
                )
            )
            return
        
        # 成功 → 結果ファイルを探してSlackに投稿
        print(f"✅ マッチング処理完了")
        print(f"📤 Slackへの結果投稿を開始...")
        
        # 最新の結果ファイルを探す
        results_dir = project_dir / "workspace" / "output"
        summary_files = sorted(results_dir.glob("matching_*_summary.md"), reverse=True)
        csv_files = sorted(results_dir.glob("matching_*.csv"), reverse=True)
        
        if summary_files and csv_files:
            latest_summary = summary_files[0]
            latest_csv = csv_files[0]
            
            print(f"📄 サマリーファイル: {latest_summary}")
            print(f"📊 CSVファイル: {latest_csv}")
            
            try:
                # サマリー読み込み
                with open(latest_summary, 'r', encoding='utf-8') as f:
                    summary_text = f.read()
                    f.seek(0)
                    first_line = f.readline().strip()
                
                # 職種名を抽出
                if '(' in first_line and ')' in first_line:
                    job_title = first_line.split('(')[1].split(')')[0]
                else:
                    job_title = "求人"
                
                # CSV行数をカウント（ヘッダー除く）
                with open(latest_csv, 'r', encoding='utf-8') as f:
                    candidate_count = sum(1 for line in f) - 1
                
                canvas_title = f"【{job_id}】{job_title} - マッチング結果"
                
                # Canvas作成（スレッド内に投稿）
                print(f"📝 Canvas作成中: {canvas_title}")
                canvas_response = client.canvases_create(
                    title=canvas_title,
                    document_content={
                        "type": "markdown",
                        "markdown": summary_text
                    }
                )
                
                canvas_id = canvas_response['canvas_id']
                print(f"✅ Canvas作成完了: {canvas_id}")
                
                # チャンネルに共有（アクセス権付与）
                client.canvases_access_set(
                    canvas_id=canvas_id,
                    access_level="read",
                    channel_ids=[channel_id]
                )
                
                # Canvas URLを構築
                auth = client.auth_test()
                team_id = auth['team_id']
                workspace_url = auth['url']
                canvas_url = f"{workspace_url}docs/{team_id}/{canvas_id}"
                
                print(f"📊 Canvas URL: {canvas_url}")
                
                # メッセージ更新（完了）
                client.chat_update(
                    channel=channel_id,
                    ts=status_ts,
                    text=(
                        f"✅ 求人レコメンドが完了しました\n\n"
                        f"求人ID: `{job_id}`\n"
                        f"職種: {job_title}\n"
                        f"見つかった候補者: *{candidate_count}名*\n"
                        f"⏱️ 処理時間: {elapsed_str}\n"
                        f"⏰ 完了時刻: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"📄 詳細はCanvasとCSVをご確認ください\n"
                        f"{canvas_url}"
                    )
                )
                
                # CSVファイルをアップロード（スレッド内）
                print(f"📤 CSVファイルアップロード中...")
                client.files_upload_v2(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    file=str(latest_csv),
                    title=f"求人レコメンド結果 ({candidate_count}名)",
                    initial_comment=f"📊 全{candidate_count}名の詳細データ（CSV形式）"
                )
                
                print(f"✅ Slack投稿完了")
                
            except Exception as post_error:
                print(f"⚠️  Slack投稿でエラー: {post_error}")
                import traceback
                traceback.print_exc()
                
                # メッセージ更新（警告）
                client.chat_update(
                    channel=channel_id,
                    ts=status_ts,
                    text=(
                        f"⚠️ 処理は完了しましたが、結果の投稿でエラーが発生しました\n\n"
                        f"求人ID: `{job_id}`\n"
                        f"⏱️ 処理時間: {elapsed_str}\n\n"
                        f"以下のファイルを手動でご確認ください:\n"
                        f"サマリー: `{latest_summary.name}`\n"
                        f"CSV: `{latest_csv.name}`"
                    )
                )
        else:
            print(f"⚠️  結果ファイルが見つかりません")
            # メッセージ更新（警告）
            client.chat_update(
                channel=channel_id,
                ts=status_ts,
                text=(
                    f"⚠️ 処理は完了しましたが、結果ファイルが見つかりませんでした\n\n"
                    f"求人ID: `{job_id}`\n"
                    f"⏱️ 処理時間: {elapsed_str}\n\n"
                    f"お手数ですが、もう一度お試しください"
                )
            )
        
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        print(f"⏱️  タイムアウト（経過時間: {elapsed_str}）")
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"⏱️ タイムアウト: 処理に10分以上かかっています\n\n"
                f"求人ID: `{job_id}`\n"
                f"経過時間: {elapsed_str}\n\n"
                f"申し訳ございません。もう一度お試しください"
            )
        )
    except FileNotFoundError as e:
        elapsed_time = time.time() - start_time
        print(f"❌ ファイルエラー: {e}")
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"❌ システムエラーが発生しました\n\n"
                f"スクリプトが見つかりません\n"
                f"管理者にお問い合わせください"
            )
        )
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 予期しないエラー: {e}")
        
        # 詳細なスタックトレース
        import traceback
        traceback.print_exc()
        
        client.chat_update(
            channel=channel_id,
            ts=status_ts,
            text=(
                f"❌ 予期しないエラーが発生しました\n\n"
                f"申し訳ございません。もう一度お試しいただくか、\n"
                f"管理者にお問い合わせください"
            )
        )
    finally:
        print(f"{'='*60}\n")

def job_worker():
    """キュー内のジョブを1件ずつ処理するワーカー"""
    global is_processing
    
    while True:
        try:
            # キューからジョブを取得（ブロッキング）
            job_data = job_queue.get()
            
            with processing_lock:
                is_processing = True
            
            # ジョブ実行
            job_data['func'](*job_data['args'], **job_data['kwargs'])
            
            job_queue.task_done()
            
            with processing_lock:
                is_processing = False
                
        except Exception as e:
            print(f"❌ ワーカーエラー: {e}")
            with processing_lock:
                is_processing = False

def handle_reload_signal(signum, frame):
    """SIGHUPシグナルを受けてコード更新→再起動"""
    print(f"\n{'='*60}")
    print(f"🔄 SIGHUP受信: コード更新を開始します")
    print(f"{'='*60}")
    
    try:
        project_dir = Path(__file__).parent.parent.resolve()
        updater_script = project_dir / "bin" / "updater.py"
        
        print(f"📥 updater.py 実行中...")
        result = subprocess.run(
            ['uv', 'run', str(updater_script)],
            capture_output=True,
            text=True,
            cwd=str(project_dir),
            timeout=30
        )
        
        print(result.stdout)
        
        # 更新があったかチェック
        if "更新しました" in result.stdout or "updated" in result.stdout.lower():
            print("✅ コード更新完了。再起動します...")
            if ADMIN_CHANNEL:
                try:
                    app.client.chat_postMessage(
                        channel=ADMIN_CHANNEL,
                        text="🔄 SIGHUP受信: コード更新後、再起動します"
                    )
                except:
                    pass
            
            time.sleep(1)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print("ℹ️ 更新なし。そのまま継続します")
            if ADMIN_CHANNEL:
                try:
                    app.client.chat_postMessage(
                        channel=ADMIN_CHANNEL,
                        text="🔄 SIGHUP受信: コードは最新です（再起動なし）"
                    )
                except:
                    pass
    
    except Exception as e:
        print(f"❌ リロードエラー: {e}")
        if ADMIN_CHANNEL:
            try:
                app.client.chat_postMessage(
                    channel=ADMIN_CHANNEL,
                    text=f"❌ SIGHUP処理でエラー: {e}"
                )
            except:
                pass

def run_download():
    """download.pyを定期実行してSlack通知"""
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"⏰ 定期実行: データダウンロード開始")
    print(f"{'='*60}")
    print(f"   開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        project_dir = Path(__file__).parent.parent.resolve()
        download_script = project_dir / "bin" / "download.py"
        
        print(f"📝 スクリプト実行中: {download_script}")
        
        result = subprocess.run(
            ["uv", "run", str(download_script)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=3600  # 1時間
        )
        
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        
        print(f"⏱️  処理時間: {elapsed_str}")
        
        if result.returncode == 0:
            # 成功
            print(f"✅ データダウンロード完了")
            if ADMIN_CHANNEL:
                app.client.chat_postMessage(
                    channel=ADMIN_CHANNEL,
                    text=(
                        f"✅ データダウンロード完了\n\n"
                        f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"⏱️ 処理時間: {elapsed_str}"
                    )
                )
        else:
            # 失敗
            print(f"❌ データダウンロード失敗")
            error_output = result.stderr[:1000] if result.stderr else result.stdout[:1000]
            if ADMIN_CHANNEL:
                app.client.chat_postMessage(
                    channel=ADMIN_CHANNEL,
                    text=(
                        f"❌ データダウンロード失敗\n\n"
                        f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"⏱️ 処理時間: {elapsed_str}\n\n"
                        f"エラー内容:\n```\n{error_output}\n```"
                    )
                )
    
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        elapsed_str = f"{int(elapsed_time // 60)}分{int(elapsed_time % 60)}秒"
        print(f"⏱️  タイムアウト（経過時間: {elapsed_str}）")
        if ADMIN_CHANNEL:
            app.client.chat_postMessage(
                channel=ADMIN_CHANNEL,
                text=f"⏱️ データダウンロードがタイムアウトしました（1時間超過）\n経過時間: {elapsed_str}"
            )
    
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        if ADMIN_CHANNEL:
            app.client.chat_postMessage(
                channel=ADMIN_CHANNEL,
                text=f"❌ データダウンロードで予期しないエラー:\n```\n{str(e)}\n```"
            )
    
    finally:
        print(f"{'='*60}\n")

def job_scheduler():
    """バックグラウンドスケジューラー（定期実行）"""
    # 毎日8時にダウンロード実行
    schedule.every().day.at("08:00").do(run_download)
    
    print("⏰ スケジューラー起動: 毎日8時にデータダウンロード実行")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1分ごとにチェック

@app.event("app_mention")
def handle_mention(event, say, logger, client):
    """ボットがメンションされた時"""
    print(f"\n{'='*60}")
    print(f"📨 メンション受信!")
    print(f"{'='*60}")
    logger.info(f"イベント内容: {event}")
    
    text = event.get('text', '').strip()
    user_id = event.get('user')
    channel_id = event.get('channel')
    thread_ts = event.get('ts')  # このメッセージ自体のタイムスタンプ（スレッドの親になる）
    
    print(f"📝 受信テキスト: {text}")
    print(f"👤 送信者: {user_id}")
    print(f"📍 チャンネル: {channel_id}")
    print(f"🧵 スレッド: {thread_ts}")
    
    # メンションを除去してコマンドを抽出
    import re
    command_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    # コマンドをパース
    parts = command_text.split()
    print(f"🔍 パース結果: {parts}")
    
    # キューの状態を確認
    queue_size = job_queue.qsize()
    with processing_lock:
        currently_processing = is_processing
    
    print(f"📊 キュー状態: {queue_size}件待機中, 処理中: {'はい' if currently_processing else 'いいえ'}")
    
    if not parts:
        # ヘルプメッセージ（スレッド内に返信）
        bot_mention = f"@{BOT_NAME}" if BOT_NAME else "@bot"
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=(
                "こんにちは！レコメンド・探索機能が使えます 👋\n\n"
                "*使い方:*\n"
                f"• `{bot_mention} job J-XXXXXXX` - 求人に合う候補者をレコメンド\n"
                f"• `{bot_mention} company SaaS系スタートアップ` - 検索クエリで企業を探索\n"
                f"• `{bot_mention} ping` - Bot稼働状況確認\n"
                f"• `{bot_mention} test` - OpenCode疎通テスト\n"
                f"• `{bot_mention} reload` - コードをリロード\n\n"
                "*企業探索の例:*\n"
                f"• `{bot_mention} company リモートワークOK`\n"
                f"• `{bot_mention} company フィンテック 金融`\n"
                f"• `{bot_mention} company AI/ML スタートアップ`\n\n"
                f"📊 現在のキュー: {queue_size}件待機中"
            )
        )
        return
    
    command = parts[0].lower()
    print(f"⚡ 実行コマンド: {command}")
    
    if command == 'job':
        # 求人レコメンド
        if len(parts) < 2:
            bot_mention = f"@{BOT_NAME}" if BOT_NAME else "@bot"
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 求人IDを指定してください\n例: `{bot_mention} job J-0000023845`"
            )
            return
        
        job_id = parts[1]
        bot_mention = f"@{BOT_NAME}" if BOT_NAME else "@bot"
        
        # まず受付メッセージ（スレッド内に即座に表示）
        if queue_size > 0:
            # 他のジョブが処理中
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=(
                    f"📋 リクエストを受け付けました\n\n"
                    f"求人ID: `{job_id}`\n"
                    f"⏳ 現在{queue_size}件処理中です\n\n"
                    f"順番が来たらこのスレッドで通知します"
                )
            )
        else:
            # すぐに処理開始
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=(
                    f"📋 リクエストを受け付けました\n\n"
                    f"求人ID: `{job_id}`\n"
                    f"⚡ すぐに処理を開始します"
                )
            )
        
        job_queue.put({
            'func': process_job_recommendation,
            'args': (job_id, user_id, say, client, channel_id, thread_ts),
            'kwargs': {}
        })
        
        print(f"✅ ジョブをキューに追加（キュー: {job_queue.qsize()}件）")
    
    elif command == 'company':
        # 企業探索（検索クエリ型）
        if len(parts) < 2:
            bot_mention = f"@{BOT_NAME}" if BOT_NAME else "@bot"
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=(
                    "❌ 検索クエリを指定してください\n\n"
                    "例:\n"
                    f"• `{bot_mention} company SaaS系スタートアップ`\n"
                    f"• `{bot_mention} company リモートワークOKの企業`\n"
                    f"• `{bot_mention} company フィンテック`"
                )
            )
            return
        
        # 検索クエリを抽出（2番目以降の全ての単語を結合）
        search_query = ' '.join(parts[1:])
        
        # まず受付メッセージ（スレッド内に即座に表示）
        if queue_size > 0:
            # 他のジョブが処理中
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=(
                    f"📋 リクエストを受け付けました\n\n"
                    f"検索クエリ: `{search_query}`\n"
                    f"⏳ 現在{queue_size}件処理中です\n\n"
                    f"順番が来たらこのスレッドで通知します"
                )
            )
        else:
            # すぐに処理開始
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=(
                    f"📋 リクエストを受け付けました\n\n"
                    f"検索クエリ: `{search_query}`\n"
                    f"⚡ すぐに処理を開始します"
                )
            )
        
        job_queue.put({
            'func': process_company_search,
            'args': (search_query, user_id, say, client, channel_id, thread_ts),
            'kwargs': {}
        })
        
        print(f"✅ ジョブをキューに追加（キュー: {job_queue.qsize()}件）")
    
    elif command == 'reload':
        # コード再読み込み
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="🔄 GitHubから最新コードを取得します..."
        )
        
        try:
            project_dir = Path(__file__).parent.parent.resolve()
            updater_script = project_dir / "bin" / "updater.py"
            result = subprocess.run(
                ['uv', 'run', str(updater_script)],
                capture_output=True,
                text=True,
                cwd=str(project_dir),
                timeout=30
            )
            
            # 結果を表示
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"```\n{result.stdout}\n```"
            )
            
            # 更新があった場合は再起動
            if "更新しました" in result.stdout:
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text="✅ 更新完了。再起動します...\n数秒お待ちください。"
                )
                
                # 少し待ってから再起動
                time.sleep(1)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            
        except subprocess.TimeoutExpired:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text="❌ 更新処理がタイムアウトしました"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ 更新エラー: {e}"
            )
    
    elif command == 'ping':
        # ヘルスチェック
        # 環境変数の確認
        env_status = []
        required_env_vars = {
            'SALESFORCE_CREDENTIALS': 'Salesforce認証',
            'SLACK_BOT_TOKEN': 'Slackボット',
            'SLACK_APP_TOKEN': 'Slack App',
            'SLACK_CH': '通知チャンネル',
        }
        
        for var_name, var_desc in required_env_vars.items():
            value = os.getenv(var_name)
            if value:
                # 値の長さだけ表示（セキュリティのため）
                env_status.append(f"✅ {var_desc}: 設定済み ({len(value)}文字)")
            else:
                env_status.append(f"❌ {var_desc}: 未設定")
        
        # OpenCode設定の確認
        opencode_model = os.getenv('OPENCODE_MODEL', '未設定（デフォルト使用）')
        opencode_api_key = os.getenv('OPENCODE_API_KEY')
        if opencode_api_key:
            env_status.append(f"✅ OpenCodeモデル: {opencode_model}")
            env_status.append(f"✅ OpenCode APIキー: 設定済み ({len(opencode_api_key)}文字)")
        else:
            env_status.append(f"ℹ️ OpenCodeモデル: {opencode_model}")
            env_status.append(f"ℹ️ OpenCode APIキー: 未設定（無料モデル使用）")
        
        # ツールの確認
        tools_status = []
        try:
            # uv の確認
            uv_result = subprocess.run(['which', 'uv'], capture_output=True, text=True, timeout=5)
            if uv_result.returncode == 0:
                uv_path = uv_result.stdout.strip()
                uv_version = subprocess.run(['uv', '--version'], capture_output=True, text=True, timeout=5)
                tools_status.append(f"✅ uv: {uv_version.stdout.strip()} ({uv_path})")
            else:
                tools_status.append(f"❌ uv: 未インストール")
        except Exception as e:
            tools_status.append(f"⚠️ uv: 確認エラー ({str(e)[:50]})")
        
        try:
            # OpenCode CLI の確認
            opencode_result = subprocess.run(['which', 'opencode'], capture_output=True, text=True, timeout=5)
            if opencode_result.returncode == 0:
                opencode_path = opencode_result.stdout.strip()
                opencode_version = subprocess.run(['opencode', '--version'], capture_output=True, text=True, timeout=5)
                tools_status.append(f"✅ OpenCode CLI: {opencode_version.stdout.strip()} ({opencode_path})")
            else:
                tools_status.append(f"❌ OpenCode CLI: 未インストール")
        except Exception as e:
            tools_status.append(f"⚠️ OpenCode CLI: 確認エラー ({str(e)[:50]})")
        
        # レスポンス作成
        response_text = (
            f"🏓 pong!\n\n"
            f"⏰ 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 キュー: {queue_size}件待機中\n\n"
            f"**環境変数:**\n" + "\n".join(env_status) + "\n\n"
            f"**ツール:**\n" + "\n".join(tools_status) + "\n\n"
            f"✅ Bot は正常に稼働しています"
        )
        
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=response_text
        )
    
    elif command == 'test':
        # OpenCode疎通確認
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="🧪 OpenCode疎通テストを開始します..."
        )
        
        try:
            # env.py の test_opencode() を使用
            import sys
            env_path = Path(__file__).parent / 'env.py'
            sys.path.insert(0, str(env_path.parent))
            
            from env import test_opencode
            
            result = test_opencode()
            
            if result['status'] == 'ok':
                # 成功
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=(
                        f"✅ OpenCode疎通テスト成功\n\n"
                        f"**モデル:** {result['model']}\n"
                        f"**プロンプト:** {result['prompt']}\n"
                        f"**結果:**\n```\n{result['output'][:500]}\n```\n\n"
                        f"OpenCodeは正常に動作しています！"
                    )
                )
            elif result['status'] == 'timeout':
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text="⏱️ OpenCodeテストがタイムアウトしました（30秒超過）"
                )
            else:
                # エラー
                error_msg = result.get('error', '不明なエラー')
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=(
                        f"❌ OpenCode疎通テスト失敗\n\n"
                        f"**エラー内容:**\n```\n{error_msg[:500]}\n```\n\n"
                        f"OpenCodeの設定を確認してください"
                    )
                )
        
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"❌ テスト実行エラー: {e}"
            )
    
    else:
        # 不明なコマンド
        bot_mention = f"@{BOT_NAME}" if BOT_NAME else "@bot"
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=(
                f"❌ 不明なコマンド: `{command}`\n\n"
                "*使えるコマンド:*\n"
                f"• `{bot_mention} job J-XXXXXXX` - 求人レコメンド\n"
                f"• `{bot_mention} company <検索クエリ>` - 企業探索\n"
                f"• `{bot_mention} ping` - Bot稼働状況確認\n"
                f"• `{bot_mention} test` - OpenCode疎通テスト\n"
                f"• `{bot_mention} reload` - コードリロード\n\n"
                "*企業探索の例:*\n"
                f"• `{bot_mention} company SaaS系スタートアップ`\n"
                f"• `{bot_mention} company リモートワークOK`"
            )
        )

@app.event("message")
def handle_message_events(body, logger):
    """メッセージイベント（ログ用）"""
    logger.debug(body)

if __name__ == "__main__":
    # 環境変数チェック
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN が設定されていません")
        print("   .env ファイルに SLACK_BOT_TOKEN=xoxb-... を追加してください")
        exit(1)
    
    if not app_token:
        print("❌ SLACK_APP_TOKEN が設定されていません")
        print("   .env ファイルに SLACK_APP_TOKEN=xapp-... を追加してください")
        exit(1)
    
    # ログレベルを設定
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # 接続テスト
    print("=" * 60)
    print("⚡️ Slackボット起動中...")
    print("=" * 60)
    print(f"📁 プロジェクトディレクトリ: {Path(__file__).parent.parent.resolve()}")
    print(f"🔑 ボットトークン: {bot_token[:20]}...")
    print(f"🔑 アプリトークン: {app_token[:20]}...")
    print()
    
    # Bot認証確認
    try:
        auth_response = app.client.auth_test()
        BOT_NAME = auth_response['user']
        print("✅ Bot認証成功")
        print(f"   Bot名: {BOT_NAME}")
        print(f"   Bot ID: {auth_response['user_id']}")
        print(f"   Team: {auth_response['team']}")
    except Exception as e:
        print(f"❌ Bot認証失敗: {e}")
        exit(1)
    
    print()
    print("=" * 60)
    print("🤖 Socket Mode接続中...")
    print("=" * 60)
    print("   Slackのボットステータスが緑●になるまで待ってください")
    print()
    
    handler = SocketModeHandler(app, app_token)
    
    print("✅ 起動完了！Slackでボットにメンションしてください")
    print()
    print("📖 使い方:")
    print(f"   @{BOT_NAME} job J-0000023845              # 求人レコメンド")
    print(f"   @{BOT_NAME} company SaaS系スタートアップ  # 企業探索")
    print(f"   @{BOT_NAME} ping                          # ヘルスチェック")
    print(f"   @{BOT_NAME} test                          # OpenCode疎通テスト")
    print(f"   @{BOT_NAME} reload                        # コードリロード")
    print()
    print("🔄 ジョブキュー: 有効（並列実行を防止し、1件ずつ順番に処理）")
    print("⏰ スケジューラー: 有効（毎日8時にデータダウンロード実行）")
    print()
    print("🛑 停止するには Ctrl+C を押してください")
    print("=" * 60)
    print()
    
    # スケジューラースレッド起動
    scheduler_thread = threading.Thread(target=job_scheduler, daemon=True)
    scheduler_thread.start()
    print("⏰ スケジューラースレッド起動完了")
    
    # ワーカースレッド起動
    worker_thread = threading.Thread(target=job_worker, daemon=True)
    worker_thread.start()
    print("🔧 ワーカースレッド起動完了\n")
    
    # SIGHUPハンドラー登録（リロード用）
    signal.signal(signal.SIGHUP, handle_reload_signal)
    print("🔄 SIGHUPハンドラー登録完了（リロード対応）\n")
    
    handler = SocketModeHandler(app, app_token)
    handler.start()
