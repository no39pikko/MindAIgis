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
    page_icon="🔧",
    layout="wide"
)

# タイトル
st.title("🔧 MindAIgis - 保守運用AIアシスタント (MVP)")
st.markdown("**Zabbixアラートから類似対応事例を検索**")

# サイドバー
with st.sidebar:
    st.header("⚙️ システム情報")

    # ヘルスチェック
    if st.button("🏥 ヘルスチェック"):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                st.success("✅ API: 正常")

                if health.get("qdrant") == "healthy":
                    st.success("✅ Qdrant: 正常")
                    if "qdrant_info" in health:
                        info = health["qdrant_info"]
                        st.info(f"📊 インデックス数: {info.get('points_count', 0)} 件")
                else:
                    st.error(f"❌ Qdrant: {health.get('qdrant')}")

                if health.get("redmine") == "healthy":
                    st.success("✅ Redmine: 正常")
                else:
                    st.error(f"❌ Redmine: {health.get('redmine')}")
            else:
                st.error("❌ API接続エラー")
        except Exception as e:
            st.error(f"❌ 接続失敗: {str(e)}")

    st.divider()

    # コレクション情報
    st.subheader("📦 インデックス情報")
    try:
        response = requests.get(f"{API_BASE_URL}/collection/info", timeout=5)
        if response.status_code == 200:
            info = response.json()
            st.metric("インデックス済みチケット", info.get("points_count", 0))
            st.caption(f"コレクション: {info.get('name', 'N/A')}")
    except:
        st.caption("情報取得失敗")

# メインコンテンツ
tab1, tab2 = st.tabs(["🔍 アラート検索", "📝 チケットインデックス"])

# タブ1: アラート検索
with tab1:
    st.header("Zabbixアラート類似検索")

    # アラート入力フォーム
    col1, col2 = st.columns([3, 1])

    with col1:
        alert_text = st.text_area(
            "アラート内容を入力",
            placeholder="例: disk usage over 90% on web-prod-01",
            height=100,
            help="Zabbixのアラートメッセージを入力してください"
        )

    with col2:
        search_limit = st.slider(
            "検索件数",
            min_value=1,
            max_value=20,
            value=5,
            help="類似チケットの取得件数"
        )

        search_button = st.button(
            "🔍 検索",
            type="primary",
            use_container_width=True
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
                            if similarity_percent >= 90:
                                color = "🟢"
                            elif similarity_percent >= 70:
                                color = "🟡"
                            else:
                                color = "🔴"

                            with st.expander(
                                f"{color} #{ticket['ticket_id']} - {ticket['subject']} "
                                f"(類似度: {similarity_percent:.1f}%)",
                                expanded=(idx == 1)  # 最初の結果だけ展開
                            ):
                                # チケット詳細
                                col_a, col_b, col_c = st.columns(3)

                                with col_a:
                                    st.markdown("**📋 基本情報**")
                                    st.write(f"チケットID: #{ticket['ticket_id']}")
                                    st.write(f"カテゴリ: {ticket.get('category', 'N/A')}")
                                    st.write(f"担当者: {ticket.get('assigned_to', 'N/A')}")

                                with col_b:
                                    st.markdown("**📅 日時情報**")
                                    if ticket.get('closed_on'):
                                        closed_date = datetime.fromisoformat(
                                            ticket['closed_on'].replace('Z', '+00:00')
                                        )
                                        st.write(f"完了日: {closed_date.strftime('%Y-%m-%d %H:%M')}")
                                    else:
                                        st.write("完了日: N/A")
                                    st.write(f"ステータス: {ticket.get('status', 'N/A')}")

                                with col_c:
                                    st.markdown("**🎯 類似度**")
                                    st.progress(ticket['similarity'])
                                    st.write(f"{similarity_percent:.1f}%")

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

# タブ2: チケットインデックス
with tab2:
    st.header("Redmineチケットのインデックス")

    st.markdown("""
    このセクションでは、Redmineチケットをベクトルデータベースに手動でインデックスできます。

    **初期セットアップ時は、別途 `scripts/index_tickets.py` を実行してください。**
    """)

    ticket_id_input = st.number_input(
        "インデックスするチケットID",
        min_value=1,
        step=1,
        help="RedmineのチケットIDを入力"
    )

    if st.button("📥 チケットをインデックス", type="primary"):
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

    st.divider()

    # 削除機能
    st.subheader("🗑️ インデックスから削除")
    delete_ticket_id = st.number_input(
        "削除するチケットID",
        min_value=1,
        step=1,
        key="delete_ticket"
    )

    if st.button("🗑️ 削除", type="secondary"):
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

# フッター
st.divider()
st.caption("MindAIgis v0.1.0 - Maintenance AI Assistant MVP")
