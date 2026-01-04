#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛠️  OpenMatching 初回セットアップ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# root権限チェック
if [ "$EUID" -ne 0 ]; then 
  echo "❌ このスクリプトはroot権限で実行してください"
  echo "   sudo bash /opt/openmatching/deploy/setup.sh"
  exit 1
fi

DEPLOY_USER="${SUDO_USER:-openmatching}"
PROJECT_ROOT="/opt/openmatching"

echo "📋 実行ユーザー: ${DEPLOY_USER}"
echo "📁 プロジェクトパス: ${PROJECT_ROOT}"
echo ""

# Step 1: uv インストール
echo "📦 Step 1: uv をインストール中..."
if ! sudo -u ${DEPLOY_USER} command -v uv &> /dev/null; then
  sudo -u ${DEPLOY_USER} bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "✅ uv インストール完了"
else
  echo "✅ uv は既にインストール済み"
fi
echo ""

# Step 2: OpenCode CLI インストール
echo "🤖 Step 2: OpenCode CLI をインストール中..."
if ! sudo -u ${DEPLOY_USER} command -v opencode &> /dev/null; then
  sudo -u ${DEPLOY_USER} bash -c "curl -fsSL https://opencode.ai/install | bash"
  echo "✅ OpenCode CLI インストール完了"
else
  echo "✅ OpenCode CLI は既にインストール済み"
fi
echo ""

# Step 3: 依存関係インストール
echo "📚 Step 3: Python依存関係をインストール中..."
cd ${PROJECT_ROOT}
sudo -u ${DEPLOY_USER} bash -c "source ~/.bashrc && ~/.local/bin/uv sync"
echo "✅ 依存関係インストール完了"
echo ""

# Step 4: systemd service 登録
echo "⚙️  Step 4: systemd service を登録中..."
cp ${PROJECT_ROOT}/deploy/openmatching-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable openmatching-bot
systemctl start openmatching-bot
echo "✅ サービス登録・起動完了"
echo ""

# 状態確認
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 サービス状態:"
systemctl status openmatching-bot --no-pager -n 10 || true
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ セットアップ完了！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 次のステップ:"
echo "   1. ログ確認: sudo journalctl -u openmatching-bot -f"
echo "   2. Slackで @bot ping と送信して動作確認"
echo "   3. 毎朝8時にデータダウンロードが自動実行されます"
