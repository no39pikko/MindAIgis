#!/bin/bash
# MindAIgis セットアップ検証スクリプト

echo "========================================="
echo "  MindAIgis セットアップ検証"
echo "========================================="
echo ""

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1 が見つかりません"
        ((ERRORS++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${YELLOW}⚠${NC} $1 が見つかりません"
        ((WARNINGS++))
    fi
}

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 ($(command -v $1))"
    else
        echo -e "${RED}✗${NC} $1 が見つかりません"
        ((ERRORS++))
    fi
}

echo "=== 1. 必須ファイルの確認 ==="
check_file ".env"
check_file "requirements.txt"
check_file "docker-compose.yml"
check_file "start.sh"
check_file "stop.sh"
check_file "app/main.py"
check_file "app/services/procedure_assistant_service.py"
check_file "app/services/vector_service.py"
check_file "app/services/llm_service.py"
check_file "app/services/redmine_service.py"
check_file "ui/streamlit_app.py"
echo ""

echo "=== 2. ディレクトリ構造の確認 ==="
check_dir "app"
check_dir "app/services"
check_dir "ui"
check_dir "scripts"
check_dir "venv"
check_dir "logs"
echo ""

echo "=== 3. システムコマンドの確認 ==="
check_command "python3"
check_command "docker"
check_command "curl"
echo ""

echo "=== 4. 仮想環境の確認 ==="
if [ -d "venv" ]; then
    if [ -f "venv/bin/python" ]; then
        echo -e "${GREEN}✓${NC} Python ($(venv/bin/python --version))"
    else
        echo -e "${RED}✗${NC} venv/bin/python が見つかりません"
        ((ERRORS++))
    fi

    if [ -f "venv/bin/uvicorn" ]; then
        echo -e "${GREEN}✓${NC} uvicorn インストール済み"
    else
        echo -e "${RED}✗${NC} uvicorn がインストールされていません"
        echo "    → source venv/bin/activate && pip install -r requirements.txt"
        ((ERRORS++))
    fi

    if [ -f "venv/bin/streamlit" ]; then
        echo -e "${GREEN}✓${NC} streamlit インストール済み"
    else
        echo -e "${RED}✗${NC} streamlit がインストールされていません"
        echo "    → source venv/bin/activate && pip install -r requirements.txt"
        ((ERRORS++))
    fi
else
    echo -e "${RED}✗${NC} 仮想環境が見つかりません"
    echo "    → python3 -m venv venv"
    ((ERRORS++))
fi
echo ""

echo "=== 5. 環境変数の確認 ==="
if [ -f ".env" ]; then
    # 必須の環境変数をチェック
    check_env() {
        if grep -q "^$1=" .env && ! grep -q "^$1=$" .env && ! grep -q "^$1=your" .env; then
            echo -e "${GREEN}✓${NC} $1 が設定されています"
        else
            echo -e "${YELLOW}⚠${NC} $1 が未設定または空です"
            ((WARNINGS++))
        fi
    }

    check_env "OPENAI_API_KEY"
    check_env "REDMINE_URL"
    check_env "REDMINE_API_KEY"

    # Phase 3 有効化チェック
    if grep -q "^PROCEDURE_ASSIST_ENABLED=true" .env; then
        echo -e "${GREEN}✓${NC} PROCEDURE_ASSIST_ENABLED=true (Phase 3 有効)"
    else
        echo -e "${YELLOW}⚠${NC} PROCEDURE_ASSIST_ENABLED が false または未設定"
        echo "    Phase 3 を使用する場合は true に設定してください"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC} .env ファイルが見つかりません"
    echo "    → cp .env.example .env && nano .env"
    ((ERRORS++))
fi
echo ""

echo "=== 6. Dockerサービスの確認 ==="
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker デーモンが起動しています"

        # Qdrantコンテナの確認
        if docker ps | grep -q "qdrant"; then
            echo -e "${GREEN}✓${NC} Qdrant コンテナが起動中"

            # Qdrant ヘルスチェック
            if command -v curl &> /dev/null; then
                if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
                    echo -e "${GREEN}✓${NC} Qdrant が応答しています (http://localhost:6333)"

                    # コレクションの確認
                    COLLECTION_CHECK=$(curl -s http://localhost:6333/collections/maintenance_tickets 2>/dev/null)
                    if echo "$COLLECTION_CHECK" | grep -q "result"; then
                        VECTORS_COUNT=$(echo "$COLLECTION_CHECK" | grep -o '"vectors_count":[0-9]*' | grep -o '[0-9]*')
                        if [ ! -z "$VECTORS_COUNT" ]; then
                            echo -e "${GREEN}✓${NC} maintenance_tickets コレクション: ${VECTORS_COUNT} vectors"
                            if [ "$VECTORS_COUNT" -eq 0 ]; then
                                echo -e "${YELLOW}⚠${NC} ベクトルが0件です"
                                echo "    → python scripts/index_redmine_tickets.py でインデックスを作成してください"
                                ((WARNINGS++))
                            fi
                        fi
                    else
                        echo -e "${YELLOW}⚠${NC} maintenance_tickets コレクションが見つかりません"
                        echo "    → python scripts/index_redmine_tickets.py でインデックスを作成してください"
                        ((WARNINGS++))
                    fi
                else
                    echo -e "${YELLOW}⚠${NC} Qdrant が応答していません"
                    ((WARNINGS++))
                fi
            fi
        else
            echo -e "${YELLOW}⚠${NC} Qdrant コンテナが起動していません"
            echo "    → ./start.sh または docker compose up -d"
            ((WARNINGS++))
        fi
    else
        echo -e "${RED}✗${NC} Docker デーモンが起動していません"
        echo "    → sudo systemctl start docker"
        ((ERRORS++))
    fi
else
    echo -e "${RED}✗${NC} docker コマンドが見つかりません"
    ((ERRORS++))
fi
echo ""

echo "=== 7. 実行権限の確認 ==="
if [ -x "start.sh" ]; then
    echo -e "${GREEN}✓${NC} start.sh に実行権限があります"
else
    echo -e "${YELLOW}⚠${NC} start.sh に実行権限がありません"
    echo "    → chmod +x start.sh"
    ((WARNINGS++))
fi

if [ -x "stop.sh" ]; then
    echo -e "${GREEN}✓${NC} stop.sh に実行権限があります"
else
    echo -e "${YELLOW}⚠${NC} stop.sh に実行権限がありません"
    echo "    → chmod +x stop.sh"
    ((WARNINGS++))
fi
echo ""

echo "=== 8. 起動中のサービスの確認 ==="
# FastAPI
if [ -f ".api.pid" ]; then
    API_PID=$(cat .api.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} FastAPI が起動中 (PID: $API_PID)"
        if command -v curl &> /dev/null; then
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} FastAPI が応答しています (http://localhost:8000)"
            else
                echo -e "${YELLOW}⚠${NC} FastAPI が応答していません"
                ((WARNINGS++))
            fi
        fi
    else
        echo -e "${YELLOW}⚠${NC} FastAPI PIDファイルがありますが、プロセスが見つかりません"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} FastAPI が起動していません"
    echo "    → ./start.sh"
fi

# Streamlit
if [ -f ".streamlit.pid" ]; then
    STREAMLIT_PID=$(cat .streamlit.pid)
    if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Streamlit が起動中 (PID: $STREAMLIT_PID)"
        if command -v curl &> /dev/null; then
            if curl -s http://localhost:8501 > /dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} Streamlit が応答しています (http://localhost:8501)"
            else
                echo -e "${YELLOW}⚠${NC} Streamlit が応答していません"
                ((WARNINGS++))
            fi
        fi
    else
        echo -e "${YELLOW}⚠${NC} Streamlit PIDファイルがありますが、プロセスが見つかりません"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Streamlit が起動していません"
    echo "    → ./start.sh"
fi
echo ""

echo "========================================="
echo "  検証結果"
echo "========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}すべての項目が正常です！${NC}"
    echo ""
    echo "次のステップ:"
    echo "  1. サービスが起動していない場合: ./start.sh"
    echo "  2. Web UI にアクセス: http://localhost:8501"
    echo "  3. API Docs にアクセス: http://localhost:8000/docs"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}警告: ${WARNINGS} 件の警告があります${NC}"
    echo "動作には問題ないかもしれませんが、上記の警告を確認してください。"
else
    echo -e "${RED}エラー: ${ERRORS} 件のエラーがあります${NC}"
    echo -e "${YELLOW}警告: ${WARNINGS} 件の警告があります${NC}"
    echo ""
    echo "上記のエラーを修正してから再度実行してください。"
    exit 1
fi
echo "========================================="
