import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ページ設定
st.set_page_config(
    page_title="MindAIgis - 保守AIアシスタント",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    /* メインタイトルのスタイリング */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #1e88e5 0%, #00acc1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }

    /* 検索ボックスのスタイリング */
    .search-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }

    /* カード型チケット表示 */
    .ticket-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1e88e5;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }

    .ticket-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }

    /* スコア表示 */
    .score-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    .score-high {
        background: #4caf50;
        color: white;
    }

    .score-medium {
        background: #ff9800;
        color: white;
    }

    .score-low {
        background: #f44336;
        color: white;
    }

    /* AI要約ボックス */
    .ai-summary {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
    }

    .ai-summary h3 {
        color: #667eea;
        margin-top: 0;
    }

    /* メタデータタグ */
    .meta-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1976d2;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }

    /* サイドバーのスタイル改善 */
    .css-1d391kg {
        background: #f8f9fa;
    }

    /* ボタンスタイル */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    /* プログレスバー */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.markdown('<h1 class="main-title">🤖 MindAIgis</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI駆動型保守運用アシスタント - 過去の対応事例を自然言語で検索</p>', unsafe_allow_html=True)

# サイドバー
with st.sidebar:
    st.markdown("### ⚙️ システム設定")

    # ヘルスチェック
    with st.expander("🏥 システムステータス", expanded=False):
        if st.button("🔄 ステータス更新", use_container_width=True):
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    health = response.json()

                    # API
                    st.metric("API", "🟢 正常" if health.get("api") == "healthy" else "🔴 異常")

                    # Qdrant
                    if health.get("qdrant") == "healthy":
                        st.metric("Qdrant", "🟢 正常")
                        if "qdrant_info" in health:
                            info = health["qdrant_info"]
                            st.caption(f"📊 {info.get('points_count', 0)} チケット")
                    else:
                        st.metric("Qdrant", "🔴 異常")

                    # Redmine
                    st.metric("Redmine", "🟢 正常" if health.get("redmine") == "healthy" else "🔴 異常")
                else:
                    st.error("接続エラー")
            except Exception as e:
                st.error(f"エラー: {str(e)}")

    st.divider()

    # インデックス情報
    st.markdown("### 📊 統計情報")
    try:
        response = requests.get(f"{API_BASE_URL}/collection/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("チケット", f"{info.get('points_count', 0)}")
            with col2:
                st.metric("ベクトル", f"{info.get('vectors_count', 0)}")
    except:
        st.caption("情報取得失敗")

    st.divider()

    # クイックアクション
    st.markdown("### ⚡ クイックアクション")

    if st.button("📥 チケットインデックス", use_container_width=True):
        st.session_state.show_index_modal = True

    if st.button("📚 ドキュメント", use_container_width=True):
        st.info("Phase 2 README: docs/PHASE2_README.md")

# メインタブ
tab1, tab2, tab3 = st.tabs(["🤖 AI検索 (Phase 2)", "🔍 通常検索 (Phase 1)", "⚙️ 管理"])

# =====================================
# タブ1: AI検索（Phase 2）
# =====================================
with tab1:
    st.markdown("### 💬 自然言語で過去の対応事例を検索")
    st.caption("例: 「先月web-prod-01でディスク容量のアラートが出たときどう対応した？」")

    # 検索フォーム
    query = st.text_area(
        "質問を入力してください",
        placeholder="先月web-prod-01でディスク容量のアラートが出たときどう対応した？\n昨日のメモリ不足エラーの解決方法は？\n2024年10月のネットワーク障害について教えて",
        height=100,
        label_visibility="collapsed"
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_ai_button = st.button(
            "🤖 AI検索を実行",
            type="primary",
            use_container_width=True,
            key="ai_search_btn"
        )

    with col2:
        ai_limit = st.selectbox(
            "取得件数",
            [5, 10, 15, 20],
            index=1,
            key="ai_limit"
        )

    with col3:
        include_context = st.checkbox(
            "外部データ取得",
            value=True,
            help="CMDB等の外部データを取得（有効な場合）"
        )

    # AI検索実行
    if search_ai_button and query:
        with st.spinner("🤖 AIが過去の事例を分析中..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/search/intelligent",
                    json={
                        "query": query,
                        "limit": ai_limit,
                        "include_context": include_context
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()

                    # クエリ分析結果
                    with st.expander("🔍 クエリ解析結果", expanded=False):
                        analysis = result.get("query_analysis", {})

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.markdown("**🔑 抽出キーワード**")
                            keywords = analysis.get("keywords", [])
                            if keywords:
                                for kw in keywords:
                                    st.markdown(f'<span class="meta-tag">{kw}</span>', unsafe_allow_html=True)
                            else:
                                st.caption("なし")

                        with col_b:
                            st.markdown("**🖥️ サーバー名**")
                            servers = analysis.get("server_names", [])
                            if servers:
                                for srv in servers:
                                    st.markdown(f'<span class="meta-tag">{srv}</span>', unsafe_allow_html=True)
                            else:
                                st.caption("なし")

                        with col_c:
                            st.markdown("**📅 日付範囲**")
                            date_range = analysis.get("date_range")
                            if date_range:
                                st.caption(f"{date_range.get('start')} 〜 {date_range.get('end')}")
                            else:
                                st.caption("指定なし")

                    st.divider()

                    # AI要約を大きく表示
                    summary = result.get("summary", "")
                    if summary:
                        st.markdown("### 📋 AI要約")
                        st.markdown(f"""
                        <div class="ai-summary">
                            {summary.replace(chr(10), '<br>')}
                        </div>
                        """, unsafe_allow_html=True)

                    st.divider()

                    # 検索結果
                    search_results = result.get("search_results", [])
                    metadata = result.get("metadata", {})

                    if search_results:
                        st.markdown(f"### 🎯 関連チケット ({metadata.get('total_results', 0)}件)")

                        for idx, ticket in enumerate(search_results, 1):
                            similarity = ticket.get("similarity", 0)
                            similarity_percent = similarity * 100

                            # スコアのスタイル決定
                            if similarity_percent >= 80:
                                score_class = "score-high"
                                emoji = "🟢"
                            elif similarity_percent >= 60:
                                score_class = "score-medium"
                                emoji = "🟡"
                            else:
                                score_class = "score-low"
                                emoji = "🔴"

                            with st.container():
                                # チケットヘッダー
                                col_h1, col_h2, col_h3 = st.columns([3, 1, 1])

                                with col_h1:
                                    st.markdown(f"#### {emoji} #{ticket.get('ticket_id')} - {ticket.get('subject')}")

                                with col_h2:
                                    st.markdown(f'<span class="{score_class} score-badge">類似度 {similarity_percent:.1f}%</span>', unsafe_allow_html=True)

                                with col_h3:
                                    comments_count = len(ticket.get("comments", []))
                                    if comments_count > 0:
                                        st.caption(f"💬 {comments_count} コメント")

                                # メタデータ
                                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

                                with meta_col1:
                                    category = ticket.get("category", "N/A")
                                    st.caption(f"📂 {category}")

                                with meta_col2:
                                    assigned = ticket.get("assigned_to", "N/A")
                                    st.caption(f"👤 {assigned}")

                                with meta_col3:
                                    status = ticket.get("status", "N/A")
                                    st.caption(f"📊 {status}")

                                with meta_col4:
                                    closed_on = ticket.get("closed_on")
                                    if closed_on:
                                        try:
                                            dt = datetime.fromisoformat(closed_on.replace('Z', '+00:00'))
                                            st.caption(f"📅 {dt.strftime('%Y-%m-%d')}")
                                        except:
                                            st.caption("📅 N/A")
                                    else:
                                        st.caption("📅 N/A")

                                # 類似度プログレスバー
                                st.progress(similarity)

                                # 詳細展開
                                with st.expander("📄 詳細を表示", expanded=(idx == 1)):
                                    # サーバー名
                                    server_names = ticket.get("server_names", [])
                                    if server_names:
                                        st.markdown("**🖥️ サーバー**")
                                        for srv in server_names:
                                            st.markdown(f'<span class="meta-tag">{srv}</span>', unsafe_allow_html=True)

                                    # 説明
                                    description = ticket.get("description", "")
                                    if description:
                                        st.markdown("**📝 問題の説明**")
                                        st.info(description[:500] + ("..." if len(description) > 500 else ""))

                                    # 解決策
                                    resolution = ticket.get("resolution", "")
                                    if resolution:
                                        st.markdown("**✅ 解決策**")
                                        st.success(resolution[:500] + ("..." if len(resolution) > 500 else ""))

                                    # コメント
                                    comments = ticket.get("comments", [])
                                    if comments:
                                        st.markdown(f"**💬 コメント ({len(comments)}件)**")
                                        for comment in comments[:3]:  # 最初の3件のみ表示
                                            user = comment.get("user", "Unknown")
                                            created = comment.get("created_on", "")
                                            notes = comment.get("notes", "")

                                            st.markdown(f"**{user}** - {created[:10] if created else 'N/A'}")
                                            st.caption(notes[:200] + ("..." if len(notes) > 200 else ""))

                                        if len(comments) > 3:
                                            st.caption(f"... 他 {len(comments) - 3} 件のコメント")

                                st.divider()
                    else:
                        st.warning("⚠️ 該当する事例が見つかりませんでした")

                elif response.status_code == 503:
                    st.error("❌ AI検索機能が無効です")
                    st.info("""
                    AI検索を有効にするには:
                    1. `.env` に `INTELLIGENT_SEARCH_ENABLED=true` を設定
                    2. `OPENAI_API_KEY` を設定
                    3. APIサーバーを再起動
                    """)
                else:
                    st.error(f"❌ エラー: {response.status_code}")
                    st.code(response.text)

            except requests.exceptions.Timeout:
                st.error("❌ タイムアウト: AIの処理に時間がかかっています")
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")

    elif search_ai_button:
        st.warning("⚠️ 質問を入力してください")

# =====================================
# タブ2: 通常検索（Phase 1）
# =====================================
with tab2:
    st.markdown("### 🔍 キーワードベクトル検索")
    st.caption("アラートメッセージやエラー文で類似チケットを検索")

    # 検索フォーム
    alert_text = st.text_area(
        "アラート内容を入力",
        placeholder="例: disk usage over 90% on web-prod-01\nメモリ使用率が95%を超えました",
        height=100,
        key="basic_search_input"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        search_button = st.button(
            "🔍 検索",
            type="primary",
            use_container_width=True,
            key="basic_search_btn"
        )

    with col2:
        search_limit = st.slider(
            "検索件数",
            min_value=1,
            max_value=20,
            value=5,
            key="basic_limit"
        )

    # 検索実行
    if search_button and alert_text:
        with st.spinner("🔄 検索中..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/search",
                    json={
                        "alert_text": alert_text,
                        "limit": search_limit
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    results = response.json()

                    if not results:
                        st.warning("⚠️ 類似チケットが見つかりませんでした")
                    else:
                        st.success(f"✅ {len(results)}件の類似チケットを発見")

                        # 結果表示
                        for idx, ticket in enumerate(results, 1):
                            similarity_percent = ticket["similarity"] * 100

                            # 類似度に応じた色分け
                            if similarity_percent >= 80:
                                color = "🟢"
                            elif similarity_percent >= 60:
                                color = "🟡"
                            else:
                                color = "🔴"

                            with st.expander(
                                f"{color} #{ticket['ticket_id']} - {ticket['subject']} "
                                f"(類似度: {similarity_percent:.1f}%)",
                                expanded=(idx == 1)
                            ):
                                # 類似度プログレスバー
                                st.progress(ticket['similarity'])

                                # チケット詳細
                                col_a, col_b, col_c = st.columns(3)

                                with col_a:
                                    st.markdown("**📋 基本情報**")
                                    st.write(f"チケットID: #{ticket['ticket_id']}")
                                    st.write(f"カテゴリ: {ticket.get('category', 'N/A')}")
                                    st.write(f"担当者: {ticket.get('assigned_to', 'N/A')}")

                                with col_b:
                                    st.markdown("**📅 日時情報**")
                                    closed_on = ticket.get('closed_on')
                                    if closed_on:
                                        try:
                                            closed_date = datetime.fromisoformat(closed_on.replace('Z', '+00:00'))
                                            st.write(f"完了日: {closed_date.strftime('%Y-%m-%d %H:%M')}")
                                        except:
                                            st.write("完了日: N/A")
                                    else:
                                        st.write("完了日: N/A")
                                    st.write(f"ステータス: {ticket.get('status', 'N/A')}")

                                with col_c:
                                    st.markdown("**🎯 類似度**")
                                    st.metric("", f"{similarity_percent:.1f}%")

                                # 説明
                                if ticket.get('description'):
                                    st.markdown("**📝 説明**")
                                    st.info(ticket['description'])

                                # 解決策
                                if ticket.get('resolution'):
                                    st.markdown("**✅ 解決策・対応内容**")
                                    st.success(ticket['resolution'])
                                else:
                                    st.warning("解決策が記録されていません")

                else:
                    st.error(f"❌ 検索エラー: {response.status_code}")
                    st.code(response.text)

            except requests.exceptions.Timeout:
                st.error("❌ タイムアウト: APIサーバーの応答がありません")
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")

    elif search_button:
        st.warning("⚠️ アラート内容を入力してください")

# =====================================
# タブ3: 管理
# =====================================
with tab3:
    st.markdown("### ⚙️ システム管理")

    # インデックス管理
    st.markdown("#### 📥 チケットインデックス")

    col1, col2 = st.columns(2)

    with col1:
        ticket_id_input = st.number_input(
            "インデックスするチケットID",
            min_value=1,
            step=1,
            help="RedmineのチケットIDを入力"
        )

        if st.button("📥 チケットをインデックス", type="primary", use_container_width=True):
            if ticket_id_input:
                with st.spinner(f"チケット #{ticket_id_input} をインデックス中..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/index/ticket/{ticket_id_input}",
                            timeout=30
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ {result['message']}")
                        elif response.status_code == 404:
                            st.error("❌ チケットが見つかりません")
                        else:
                            st.error(f"❌ エラー: {response.status_code}")
                            st.code(response.text)

                    except Exception as e:
                        st.error(f"❌ エラー: {str(e)}")

    with col2:
        delete_ticket_id = st.number_input(
            "削除するチケットID",
            min_value=1,
            step=1,
            key="delete_ticket"
        )

        if st.button("🗑️ インデックスから削除", type="secondary", use_container_width=True):
            if delete_ticket_id:
                with st.spinner(f"チケット #{delete_ticket_id} を削除中..."):
                    try:
                        response = requests.delete(
                            f"{API_BASE_URL}/index/ticket/{delete_ticket_id}",
                            timeout=10
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ {result['message']}")
                        else:
                            st.error(f"❌ エラー: {response.status_code}")

                    except Exception as e:
                        st.error(f"❌ エラー: {str(e)}")

    st.divider()

    # バッチインデックス
    st.markdown("#### 🔄 バッチ処理")
    st.info("""
    **全チケットの再インデックス**

    Phase 2ではコメント（ジャーナル）も検索対象になります。
    既存のチケットを再インデックスすることを推奨します。

    コマンド:
    ```bash
    python scripts/reindex_tickets_with_comments.py
    ```
    """)

# フッター
st.divider()
col_f1, col_f2, col_f3 = st.columns([1, 1, 1])

with col_f1:
    st.caption("🤖 MindAIgis v2.0.0")

with col_f2:
    st.caption("Phase 2: AI検索対応")

with col_f3:
    st.caption("Powered by OpenAI + Qdrant")
