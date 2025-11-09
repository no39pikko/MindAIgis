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
    page_title="MindAIgis - 手順書作成補佐",
    page_icon="👨‍🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    /* メインタイトル */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(120deg, #f39c12 0%, #e74c3c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .subtitle {
        font-size: 1.2rem;
        color: #555;
        margin-bottom: 2rem;
    }

    /* 先輩のアドバイスボックス */
    .senior-advice {
        background: linear-gradient(135deg, #f39c1215 0%, #e74c3c15 100%);
        border-left: 5px solid #f39c12;
        padding: 2rem;
        border-radius: 10px;
        margin: 2rem 0;
        font-size: 1.1rem;
        line-height: 1.8;
    }

    .senior-advice h3 {
        color: #f39c12;
        margin-top: 0;
        font-size: 1.3rem;
    }

    /* チケットカード */
    .ticket-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border-left: 5px solid #3498db;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .ticket-card:hover {
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        transform: translateY(-3px);
    }

    /* 重要度バッジ */
    .priority-critical {
        background: #e74c3c;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    .priority-high {
        background: #f39c12;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    .priority-medium {
        background: #3498db;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    .priority-low {
        background: #95a5a6;
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
    }

    /* 注意事項・ハマりポイント */
    .caution-box {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    .pitfall-box {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    .reference-box {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    /* タグ */
    .tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1976d2;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .tag-caution {
        background: #fff3cd;
        color: #856404;
    }

    .tag-pitfall {
        background: #f8d7da;
        color: #721c24;
    }

    .tag-config {
        background: #d1ecf1;
        color: #0c5460;
    }

    /* チケットリンク */
    .ticket-link {
        color: #3498db;
        font-weight: 600;
        text-decoration: none;
        border-bottom: 2px solid #3498db;
    }

    .ticket-link:hover {
        color: #2980b9;
        border-bottom-color: #2980b9;
    }

    /* 関係図 */
    .relationship-node {
        background: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.5rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.markdown('<h1 class="main-title">👨‍🏫 MindAIgis</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">手順書作成補佐システム - 10年選手の先輩があなたをサポート</p>', unsafe_allow_html=True)

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
                    st.metric("API", "🟢 正常" if health.get("api") == "healthy" else "🔴 異常")
                    st.metric("Qdrant", "🟢 正常" if health.get("qdrant") == "healthy" else "🔴 異常")
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

    st.markdown("### 💡 使い方")
    st.info("""
    1. 作業内容を入力
    2. 先輩がチケットを検索
    3. 重要な注意点を教えてくれます

    **例**: "FW設定Aの手順書を作りたい"
    """)

# メインコンテンツ
st.markdown("## 📝 何の手順書を作りますか？")

task_input = st.text_area(
    "作業内容を入力してください",
    placeholder="例:\n・FW設定Aの手順書を作りたい\n・新規サーバーへのミドルウェアインストール手順\n・データベース移行の手順書",
    height=100,
    key="task_input"
)

context_input = st.text_area(
    "補足情報（オプション）",
    placeholder="例: 新規サーバーへの展開で、既存FWも並行稼働中",
    height=60,
    key="context_input"
)

col1, col2 = st.columns([3, 1])

with col1:
    assist_button = st.button(
        "👨‍🏫 先輩に聞く",
        type="primary",
        use_container_width=True,
        key="assist_btn"
    )

with col2:
    if st.button("🔄 クリア", use_container_width=True):
        st.session_state.task_input = ""
        st.session_state.context_input = ""
        st.rerun()

# 補佐実行
if assist_button and task_input:
    with st.spinner("👨‍🏫 10年選手の先輩が考え中..."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/assist/procedure",
                json={
                    "task": task_input,
                    "context": context_input if context_input else None
                },
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()

                # 先輩のアドバイス
                summary = result.get("summary", "")
                if summary:
                    st.markdown("## 👨‍🏫 先輩からのアドバイス")
                    st.markdown(f"""
                    <div class="senior-advice">
                        {summary.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                # 検索戦略
                strategies = result.get("search_strategies", [])
                if strategies:
                    with st.expander("🔍 検索した視点", expanded=False):
                        for idx, strategy in enumerate(strategies, 1):
                            st.markdown(f"**{idx}. {strategy.get('perspective', 'N/A')}**")
                            st.caption(f"理由: {strategy.get('reason', 'N/A')}")
                            st.caption(f"検索クエリ: {strategy.get('search_query', 'N/A')}")
                            if idx < len(strategies):
                                st.markdown("---")

                st.divider()

                # 重要なチケット
                important_tickets = result.get("important_tickets", [])

                if important_tickets:
                    st.markdown("## 🎯 重要なチケット（重要度順）")

                    for idx, ticket in enumerate(important_tickets[:10], 1):
                        ticket_id = ticket.get("ticket_id")
                        subject = ticket.get("subject", "N/A")
                        status = ticket.get("status", "N/A")
                        similarity = ticket.get("similarity", 0) * 100

                        # 重要度の判定
                        if idx == 1:
                            priority_class = "priority-critical"
                            priority_label = "最重要"
                            emoji = "🔥"
                        elif idx <= 3:
                            priority_class = "priority-high"
                            priority_label = "重要"
                            emoji = "⚠️"
                        elif idx <= 6:
                            priority_class = "priority-medium"
                            priority_label = "確認推奨"
                            emoji = "📌"
                        else:
                            priority_class = "priority-low"
                            priority_label = "参考"
                            emoji = "📄"

                        with st.container():
                            col_h1, col_h2, col_h3 = st.columns([4, 1, 1])

                            with col_h1:
                                st.markdown(f"### {emoji} #{ticket_id} - {subject}")

                            with col_h2:
                                st.markdown(f'<span class="{priority_class}">{priority_label}</span>', unsafe_allow_html=True)

                            with col_h3:
                                st.caption(f"類似度 {similarity:.1f}%")

                            # メタデータ
                            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

                            with meta_col1:
                                st.caption(f"📊 {status}")

                            with meta_col2:
                                assigned = ticket.get("assigned_to", "N/A")
                                st.caption(f"👤 {assigned}")

                            with meta_col3:
                                closed_on = ticket.get("closed_on")
                                if closed_on:
                                    try:
                                        dt = datetime.fromisoformat(closed_on.replace('Z', '+00:00'))
                                        st.caption(f"📅 {dt.strftime('%Y-%m-%d')}")
                                    except:
                                        st.caption("📅 N/A")
                                else:
                                    st.caption("📅 進行中")

                            with meta_col4:
                                comments_count = len(ticket.get("comments", []))
                                if comments_count > 0:
                                    st.caption(f"💬 {comments_count}コメント")

                            # タグ
                            if ticket.get("has_cautions"):
                                st.markdown('<span class="tag tag-caution">⚠️ 注意事項あり</span>', unsafe_allow_html=True)

                            if ticket.get("has_pitfalls"):
                                st.markdown('<span class="tag tag-pitfall">⛔ ハマりポイントあり</span>', unsafe_allow_html=True)

                            if ticket.get("has_config_values"):
                                st.markdown('<span class="tag tag-config">📋 設定値あり</span>', unsafe_allow_html=True)

                            # 詳細
                            with st.expander("📄 詳細を表示", expanded=(idx == 1)):
                                # 注意事項
                                if ticket.get("caution_summary"):
                                    st.markdown("**⚠️ 注意事項**")
                                    st.markdown(f"""
                                    <div class="caution-box">
                                        {ticket.get("caution_summary")}
                                    </div>
                                    """, unsafe_allow_html=True)

                                # ハマりポイント
                                if ticket.get("pitfall_summary"):
                                    st.markdown("**⛔ ハマりポイント**")
                                    st.markdown(f"""
                                    <div class="pitfall-box">
                                        {ticket.get("pitfall_summary")}
                                    </div>
                                    """, unsafe_allow_html=True)

                                # 説明
                                description = ticket.get("description", "")
                                if description:
                                    st.markdown("**📝 説明**")
                                    st.info(description[:500] + ("..." if len(description) > 500 else ""))

                                # 解決策・対応内容
                                resolution = ticket.get("resolution", "")
                                if resolution:
                                    st.markdown("**✅ 解決策・対応内容**")
                                    st.success(resolution[:500] + ("..." if len(resolution) > 500 else ""))

                                # 重要コメント
                                important_comments = ticket.get("important_comments", [])
                                if important_comments:
                                    st.markdown("**💡 重要なコメント**")
                                    for comment in important_comments[:3]:
                                        comment_type = comment.get("type", "")
                                        user = comment.get("user", "Unknown")
                                        comment_summary = comment.get("summary", "")

                                        if comment_type == "caution":
                                            st.warning(f"⚠️ **{user}**: {comment_summary}")
                                        elif comment_type == "pitfall":
                                            st.error(f"⛔ **{user}**: {comment_summary}")
                                        elif comment_type == "config":
                                            st.info(f"📋 **{user}**: {comment_summary}")
                                        else:
                                            st.caption(f"💬 **{user}**: {comment_summary}")

                                # サーバー名
                                server_names = ticket.get("server_names", [])
                                if server_names:
                                    st.markdown("**🖥️ 関連サーバー**")
                                    for srv in server_names:
                                        st.markdown(f'<span class="tag">{srv}</span>', unsafe_allow_html=True)

                            st.divider()

                # 既存システムの更新
                updates = result.get("updates", [])
                if updates:
                    st.markdown("## 🆕 既存システムの更新（要反映）")
                    st.warning("⚠️ 以下の更新を新規設定にも反映する必要があります")

                    for update in updates:
                        with st.container():
                            col_u1, col_u2 = st.columns([3, 1])

                            with col_u1:
                                st.markdown(f"**チケット#{update.get('ticket_id')}**")
                                st.caption(f"{update.get('user')} - {update.get('created_on', 'N/A')[:10]}")

                            with col_u2:
                                st.markdown('<span class="tag tag-caution">要反映</span>', unsafe_allow_html=True)

                            st.info(update.get("content", ""))

                    st.divider()

                # チケット関係図
                relationships = result.get("relationships", {})
                related = relationships.get("related", [])
                references = relationships.get("references", {})

                if related or references:
                    with st.expander("🔗 チケット間の関係", expanded=False):
                        if related:
                            st.markdown("**関連チケット**")
                            for rel in related[:10]:
                                st.caption(f"チケット#{rel.get('from')} → #{rel.get('to')} ({rel.get('type', 'N/A')})")

                        if references:
                            st.markdown("**コメント内参照**")
                            for ticket_id, refs in list(references.items())[:5]:
                                st.caption(f"チケット#{ticket_id} → {', '.join([f'#{r}' for r in refs])}")

            elif response.status_code == 503:
                st.error("❌ 手順書作成補佐機能が無効です")
                st.info("""
                補佐機能を有効にするには:
                1. `.env` に `PROCEDURE_ASSIST_ENABLED=true` を設定
                2. `OPENAI_API_KEY` を設定
                3. APIサーバーを再起動
                """)
            else:
                st.error(f"❌ エラー: {response.status_code}")
                st.code(response.text)

        except requests.exceptions.Timeout:
            st.error("❌ タイムアウト: 処理に時間がかかっています（大量のチケットを分析中かもしれません）")
        except Exception as e:
            st.error(f"❌ エラー: {str(e)}")

elif assist_button:
    st.warning("⚠️ 作業内容を入力してください")

# フッター
st.divider()
col_f1, col_f2, col_f3 = st.columns([1, 1, 1])

with col_f1:
    st.caption("👨‍🏫 MindAIgis v3.0.0")

with col_f2:
    st.caption("Phase 3: 手順書作成補佐")

with col_f3:
    st.caption("10年選手の先輩があなたをサポート")
