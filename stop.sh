#!/bin/bash
# MindAIgis 停止スクリプト

echo "========================================"
echo "  MindAIgis 停止中..."
echo "========================================"

# FastAPI停止
if [ -f .api.pid ]; then
    API_PID=$(cat .api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo "FastAPI停止中 (PID: $API_PID)..."
        kill $API_PID
        rm .api.pid
        echo "✓ FastAPI停止完了"
    else
        echo "FastAPIプロセスが見つかりません"
        rm .api.pid
    fi
else
    echo "FastAPI PIDファイルが見つかりません"
fi

# Streamlit停止
if [ -f .streamlit.pid ]; then
    STREAMLIT_PID=$(cat .streamlit.pid)
    if kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "Streamlit停止中 (PID: $STREAMLIT_PID)..."
        kill $STREAMLIT_PID
        rm .streamlit.pid
        echo "✓ Streamlit停止完了"
    else
        echo "Streamlitプロセスが見つかりません"
        rm .streamlit.pid
    fi
else
    echo "Streamlit PIDファイルが見つかりません"
fi

# Qdrantコンテナ停止
echo "Qdrantコンテナ停止中..."
docker compose down
echo "✓ Qdrant停止完了"

echo ""
echo "========================================"
echo "  すべてのサービスを停止しました"
echo "========================================"
