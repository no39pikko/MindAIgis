"""
MindAIgis - 手順書作成補佐ツール
プロフェッショナルUI
"""

import streamlit as st
import requests
import os
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="MindAIgis - 手順書作成補佐",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apple風のプロフェッショナルなCSS
st.markdown("""
<style>
    /* グローバル */
    .main {
        background-color: #fafafa;
    }

    /* ヘッダー */
    .header {
        padding: 2rem 0 1rem 0;
        margin-bottom: 2rem;
    }

    .header h1 {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1d1d1f;
        margin-bottom: 0.5rem;
    }

    .header p {
        font-size: 1.1rem;
        color: #6e6e73;
        font-weight: 400;
    }

    /* 推奨事項ボックス */
    .recommendations-box {
        background: linear-gradient(135deg, #ffffff 0%, #f5f5f7 100%);
        border: 1px solid #d2d2d7;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    .recommendations-box h3 {
        color: #1d1d1f;
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .recommendations-box p {
        color: #1d1d1f;
        font-size: 1rem;
        line-height: 1.7;
        margin-bottom: 0.8rem;
    }

    /* チケットカード */
    .ticket-card {
        background: #ffffff;
        border: 1px solid #d2d2d7;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .ticket-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: #0071e3;
    }

    .ticket-header {
        display: flex;
        align-items: center;
        margin-bottom: 0.8rem;
    }

    .ticket-id {
        font-size: 0.9rem;
        color: #0071e3;
        font-weight: 500;
        margin-right: 1rem;
    }

    .ticket-title {
        font-size: 1.1rem;
        color: #1d1d1f;
        font-weight: 600;
        flex-grow: 1;
    }

    .importance-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .importance-critical {
        background: #ff3b30;
        color: white;
    }

    .importance-high {
        background: #ff9500;
        color: white;
    }

    .importance-medium {
        background: #0071e3;
        color: white;
    }

    .importance-low {
        background: #8e8e93;
        color: white;
    }

    .ticket-summary {
        color: #6e6e73;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-top: 0.5rem;
    }

    .ticket-meta {
        display: flex;
        gap: 1rem;
        margin-top: 0.8rem;
        font-size: 0.85rem;
        color: #86868b;
    }

    /* タグ */
    .tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .tag-caution {
        background: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }

    .tag-reference {
        background: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }

    /* 詳細セクション */
    .detail-section {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #d2d2d7;
    }

    .detail-section h4 {
        font-size: 1rem;
        color: #1d1d1f;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .detail-section ul {
        margin-left: 1.2rem;
        color: #6e6e73;
    }

    .detail-section li {
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }

    /* 統計情報 */
    .stats-container {
        display: flex;
        gap: 1rem;
        margin: 1.5rem 0;
    }

    .stat-box {
        background: #ffffff;
        border: 1px solid #d2d2d7;
        border-radius: 12px;
        padding: 1.2rem;
        flex: 1;
        text-align: center;
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 600;
        color: #0071e3;
    }

    .stat-label {
        font-size: 0.9rem;
        color: #6e6e73;
        margin-top: 0.3rem;
    }

    /* ボタン */
    .stButton > button {
        background: #0071e3;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 500;
        font-size: 1rem;
    }

    .stButton > button:hover {
        background: #0077ed;
    }

    /* 入力フィールド */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid #d2d2d7;
        border-radius: 8px;
        padding: 0.6rem;
    }

    /* エラー・警告 */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# API設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def main():
    # ヘッダー
    st.markdown("""
    <div class="header">
        <h1>手順書作成補佐</h1>
        <p>AIが過去のチケットを分析し、手順書作成に必要な情報を提供します</p>
    </div>
    """, unsafe_allow_html=True)

    # 入力フォーム
    col1, col2 = st.columns([3, 1])

    with col1:
        task = st.text_input(
            "作業内容",
            placeholder="例: FW設定Aの手順書を作りたい",
            label_visibility="collapsed"
        )

    with col2:
        search_button = st.button("検索", use_container_width=True, type="primary")

    # オプション（展開式）
    with st.expander("詳細オプション"):
        context = st.text_area(
            "追加コンテキスト（任意）",
            placeholder="例: 新規サーバーへの展開で、既存FWも並行稼働中",
            height=100
        )

    # 検索実行
    if search_button and task:
        with st.spinner("チケットを検索・分析中..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/assist/procedure",
                    json={
                        "task": task,
                        "context": context if context else None
                    },
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    display_results(result)
                elif response.status_code == 503:
                    st.error("手順書作成補佐機能が無効です。環境変数 PROCEDURE_ASSIST_ENABLED=true を設定してください。")
                else:
                    st.error(f"エラーが発生しました: {response.status_code}")
                    st.text(response.text)

            except requests.exceptions.Timeout:
                st.error("タイムアウトしました。処理に時間がかかっています。")
            except requests.exceptions.ConnectionError:
                st.error(f"APIサーバーに接続できません。{API_BASE_URL} が起動しているか確認してください。")
            except Exception as e:
                st.error(f"予期しないエラーが発生しました: {str(e)}")

    elif search_button:
        st.warning("作業内容を入力してください")


def display_results(result: dict):
    """検索結果を表示"""

    recommendations = result.get("recommendations", "")
    tickets = result.get("analyzed_tickets", [])
    tickets_found = result.get("tickets_found", 0)
    search_process = result.get("search_process", {})
    relationships = result.get("relationships", {})

    # 検索プロセス表示（デバッグ情報）
    if search_process:
        with st.expander("🔍 検索プロセス（複数視点検索）", expanded=True):
            # 初回検索クエリ（複数）
            initial_queries = search_process.get('initial_queries', [])
            perspectives = search_process.get('perspectives', [])

            if perspectives:
                st.markdown("**🎯 生成された検索視点:**")
                for p in perspectives:
                    st.markdown(f"  - 「**{p.get('query')}**」 ← {p.get('reason')}")
            elif initial_queries:
                st.markdown(f"**初回検索クエリ:** {', '.join(initial_queries)}")
            else:
                # 後方互換性
                st.markdown(f"**初回検索クエリ:** {search_process.get('initial_query', '不明')}")

            st.markdown(f"**初回検索結果:** {search_process.get('initial_count')}件")

            # 追加検索
            additional = search_process.get('additional_queries', [])
            if additional:
                st.markdown(f"**🔍 LLMが提案した追加検索:**")
                for aq in additional:
                    st.markdown(f"  - {aq}")

            st.markdown(f"**✅ 最終結果:** {search_process.get('total_count')}件")

    # 統計情報
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-value">{tickets_found}</div>
            <div class="stat-label">見つかったチケット</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{len(tickets)}</div>
            <div class="stat-label">分析済みチケット</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{len(relationships.get('related', []))}</div>
            <div class="stat-label">関連チケット</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # AI推奨事項
    if recommendations:
        st.markdown(f"""
        <div class="recommendations-box">
            <h3>分析結果</h3>
            {format_recommendations(recommendations)}
        </div>
        """, unsafe_allow_html=True)

    # チケット一覧
    if tickets:
        st.markdown("---")
        st.markdown("### 関連チケット")
        st.markdown(f"重要度順に{len(tickets)}件のチケットを表示しています。クリックすると詳細が表示されます。")

        for idx, ticket in enumerate(tickets):
            display_ticket_card(ticket, idx)
    else:
        st.info("該当するチケットが見つかりませんでした。")


def format_recommendations(text: str) -> str:
    """推奨事項を段落ごとにフォーマット"""
    paragraphs = text.split("\n\n")
    formatted = []
    for p in paragraphs:
        if p.strip():
            formatted.append(f"<p>{p.strip()}</p>")
    return "".join(formatted)


def display_ticket_card(ticket: dict, index: int):
    """チケットカードを表示（サムネイル+展開式）"""

    ticket_id = ticket.get("ticket_id")
    subject = ticket.get("subject", "タイトルなし")
    ai_summary = ticket.get("ai_summary", "")
    importance_score = ticket.get("importance_score", 0)
    importance_reason = ticket.get("importance_reason", "")
    key_points = ticket.get("key_points", [])
    cautions = ticket.get("cautions", [])
    references = ticket.get("references", [])
    status = ticket.get("status", "")
    similarity = ticket.get("similarity", 0)

    # 複数の視点を取得
    found_by_perspectives = ticket.get("found_by_perspectives", [])
    if found_by_perspectives:
        # 複数視点を結合
        found_by = ", ".join([p.get('reason', '不明') for p in found_by_perspectives])
    else:
        # 後方互換性（古いデータ対応）
        found_by = ticket.get("found_by_perspective", "")

    # 重要度バッジ
    if importance_score >= 90:
        badge_class = "importance-critical"
        badge_text = "必須"
    elif importance_score >= 70:
        badge_class = "importance-high"
        badge_text = "重要"
    elif importance_score >= 50:
        badge_class = "importance-medium"
        badge_text = "参考"
    else:
        badge_class = "importance-low"
        badge_text = "関連"

    # タグ
    tags = []
    if cautions:
        tags.append('<span class="tag tag-caution">⚠️ 注意点あり</span>')
    if references:
        tags.append('<span class="tag tag-reference">📌 参照情報あり</span>')

    tags_html = "".join(tags)

    # カードのサムネイル
    card_html = f"""
    <div class="ticket-card">
        <div class="ticket-header">
            <span class="ticket-id">#{ticket_id}</span>
            <span class="ticket-title">{subject}</span>
            <span class="importance-badge {badge_class}">{badge_text} ({importance_score}点)</span>
        </div>
        <div class="ticket-summary">{ai_summary if ai_summary else '要約なし'}</div>
        <div class="ticket-meta">
            <span>📊 類似度: {similarity:.2%}</span>
            <span>📂 ステータス: {status}</span>
            {f'<span>🔍 検索視点: {found_by}</span>' if found_by else ''}
        </div>
        {f'<div style="margin-top: 0.8rem;">{tags_html}</div>' if tags else ''}
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    # 展開式の詳細情報
    with st.expander(f"チケット#{ticket_id} の詳細を表示", expanded=False):
        # 検索視点の詳細（複数の場合）
        if found_by_perspectives and len(found_by_perspectives) > 1:
            st.markdown("**🔍 このチケットが見つかった検索視点**")
            for p in found_by_perspectives:
                st.markdown(f"- 「**{p.get('query')}**」 ← {p.get('reason')}")
            st.markdown("---")

        # 重要度の理由
        if importance_reason:
            st.markdown(f"**重要度評価**")
            st.info(importance_reason)

        # 主なポイント
        if key_points:
            st.markdown("**主なポイント**")
            for point in key_points:
                st.markdown(f"- {point}")

        # 注意事項
        if cautions:
            st.markdown("**⚠️ 注意事項**")
            for caution in cautions:
                st.warning(caution)

        # 参照情報
        if references:
            st.markdown("**📌 参照情報**")
            for ref in references:
                st.info(ref)

        # チケット詳細（説明文）
        description = ticket.get("description", "")
        if description:
            st.markdown("**チケット詳細**")
            with st.expander("説明文を表示", expanded=False):
                st.text(description[:1000] + ("..." if len(description) > 1000 else ""))

        # コメント
        comments = ticket.get("comments", [])
        if comments:
            st.markdown(f"**コメント ({len(comments)}件)**")
            with st.expander("コメントを表示", expanded=False):
                for idx, comment in enumerate(comments[:5], 1):
                    user = comment.get("user", "不明")
                    created = comment.get("created_on", "")
                    notes = comment.get("notes", "")
                    if notes:
                        st.markdown(f"**コメント{idx}** ({user} - {created})")
                        st.text(notes[:500] + ("..." if len(notes) > 500 else ""))
                        st.markdown("---")

                if len(comments) > 5:
                    st.info(f"他 {len(comments) - 5} 件のコメントがあります")

        # Redmineリンク
        redmine_url = os.getenv("REDMINE_URL", "http://your-redmine-server.com")
        st.markdown(f"[Redmineで開く]({redmine_url}/issues/{ticket_id})")


if __name__ == "__main__":
    main()
