# Phase 3 最終チェックリスト

## ✅ 実装完了確認

### コアファイル

- [x] `app/services/procedure_assistant_service.py` (651行) - 完全実装
- [x] `ui/streamlit_app.py` (503行) - 完全実装
- [x] `app/main.py` - Phase 3 エンドポイント追加済み
- [x] `start.sh` - AlmaLinux 9 対応完了
- [x] `stop.sh` - AlmaLinux 9 対応完了

### バグ修正

- [x] `vector_service.py`: `Optional` インポート追加済み
- [x] `procedure_assistant_service.py` line 270: モデル指定修正済み
- [x] start.sh/stop.sh: `docker compose` (V2) に変更済み

### ドキュメント

- [x] `SETUP.md` - セットアップ手順
- [x] `QUICK_START.md` - クイックスタート
- [x] `PHASE3_TESTING_GUIDE.md` - 詳細テストガイド
- [x] `IMPLEMENTATION_SUMMARY.md` - 実装サマリー
- [x] `verify_setup.sh` - 自動検証スクリプト
- [x] `FINAL_CHECKLIST.md` - このファイル

## 🚦 起動前の最終チェック

### 1. セットアップ検証を実行

```bash
cd /mnt/c/Users/aotoh/Documents/ClaudeCode/MindAIgis
./verify_setup.sh
```

**期待される結果**: すべての項目が ✓ になる

### 2. 環境変数を確認

```bash
# .env ファイルが存在するか
ls -la .env

# 必須項目が設定されているか
grep "^OPENAI_API_KEY=" .env
grep "^REDMINE_URL=" .env
grep "^REDMINE_API_KEY=" .env
grep "^PROCEDURE_ASSIST_ENABLED=true" .env
```

### 3. 仮想環境を確認

```bash
# 仮想環境が存在するか
ls -la venv/

# 必要なパッケージがインストールされているか
ls venv/bin/uvicorn
ls venv/bin/streamlit
```

もしインストールされていない場合:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Dockerを確認

```bash
# Dockerが動いているか
docker ps

# Qdrantコンテナが起動しているか（起動している必要はないが、起動可能か確認）
docker compose ps
```

## 🎯 テスト実施手順

### Step 1: システム起動

```bash
./start.sh
```

**期待される出力**:
```
========================================
  MindAIgis起動完了！
========================================

  Web UI: http://localhost:8501
  API:    http://localhost:8000
  API Docs: http://localhost:8000/docs
```

### Step 2: ヘルスチェック

```bash
# API
curl http://localhost:8000/health

# Qdrant
curl http://localhost:6333/collections

# Qdrantのデータ確認
curl http://localhost:6333/collections/maintenance_tickets
```

`maintenance_tickets` の `vectors_count` が 0 の場合:

```bash
source venv/bin/activate
python scripts/index_redmine_tickets.py
```

### Step 3: Web UIでテスト

1. ブラウザで http://localhost:8501 を開く

2. テストクエリを入力:
   ```
   DNS設定変更の手順書を作成したい
   ```

3. 「検索」ボタンをクリック

4. 確認事項:
   - [ ] 検索プロセス（デバッグ情報）が表示される
   - [ ] 初回検索クエリに「手順書」「作成」が含まれていない
   - [ ] LLMが追加検索を提案している
   - [ ] 分析結果が自然な文章で表示される
   - [ ] チケットが重要度順に表示される
   - [ ] チケットカードをクリックすると詳細が展開される

### Step 4: API Docsでテスト

1. ブラウザで http://localhost:8000/docs を開く

2. `/assist/procedure` エンドポイントを展開

3. "Try it out" をクリック

4. リクエストボディを入力:
   ```json
   {
     "task": "DNS設定変更の手順書を作成したい",
     "context": null
   }
   ```

5. "Execute" をクリック

6. 確認事項:
   - [ ] Response Code が 200
   - [ ] `recommendations` フィールドに推奨事項が含まれる
   - [ ] `analyzed_tickets` に分析済みチケットが含まれる
   - [ ] `search_process` に検索プロセスが含まれる

### Step 5: ログ確認

```bash
# APIログ
tail -50 logs/api.log

# Streamlitログ
tail -50 logs/streamlit.log
```

**期待されるAPIログの例**:
```
=== 手順書作成補佐（正しいRAG） ===
Query: DNS設定変更の手順書を作成したい

Step 1: クエリ分析
Keywords extracted: DNS設定変更

Step 2: 初回検索
Found 5 tickets

Step 3: チケット内容の分析とギャップ特定
Additional searches needed: ['ゾーンファイル', 'named.conf 設定']

Step 4: 追加検索
Total unique tickets: 12

Step 5: 詳細分析
Analyzing 12 tickets...

Step 6: 推奨事項生成
Generated recommendations.
```

## 🎓 テストケース（詳細は PHASE3_TESTING_GUIDE.md を参照）

### 基本テスト

1. **シンプルな検索**
   - 入力: "DNS設定変更の手順書を作成したい"
   - 期待: ノイズワードが除去され、関連チケットが表示される

2. **コンテキスト付き検索**
   - 入力: "ファイアウォール設定変更"
   - コンテキスト: "新規サーバーへの展開で、既存FWも並行稼働中"
   - 期待: コンテキストを考慮した分析

3. **時間フィルタ**
   - 入力: "先月のディスク容量アラートの対処方法"
   - 期待: 時間フィルタが適用される

4. **ゼロヒット**
   - 入力: "存在しない作業XYZABC"
   - 期待: エラーにならず、適切なメッセージを表示

## 🐛 トラブルシューティング

### 問題: start.sh が失敗する

```bash
# 実行権限を確認
ls -l start.sh

# なければ付与
chmod +x start.sh

# 仮想環境を確認
ls -la venv/
```

### 問題: "docker compose: command not found"

```bash
# Dockerのバージョン確認
docker --version

# Docker Composeのバージョン確認
docker compose version
```

### 問題: "uvicorn がインストールされていません"

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 問題: APIが503エラーを返す

- `.env` で `PROCEDURE_ASSIST_ENABLED=true` になっているか確認
- `logs/api.log` を確認してエラーを特定

### 問題: 検索結果が0件

```bash
# Qdrantのデータを確認
curl http://localhost:6333/collections/maintenance_tickets

# vectors_count が 0 の場合
source venv/bin/activate
python scripts/index_redmine_tickets.py
```

## 📊 パフォーマンス基準

### 正常な応答時間

- クエリ分析: 1-2秒
- 初回検索: 0.5秒
- 内容分析: 3-5秒
- 追加検索: 1-3秒
- 推奨事項生成: 3-5秒

**合計**: 約10-15秒

30秒以上かかる場合は異常と判断。

## 🎯 次のアクション

### テスト完了後

1. **実運用テスト**
   - 実際の運用員に使ってもらう
   - フィードバックを収集

2. **チューニング**
   - 検索精度の調整（score_threshold）
   - 表示内容の調整
   - パフォーマンスの最適化

3. **改善**
   - フィードバックに基づく機能追加
   - UIの改善
   - ドキュメントの充実

## 📝 完了報告テンプレート

テスト完了後、以下の情報を記録:

```
【テスト日時】
2025/XX/XX XX:XX

【テスト環境】
- OS: AlmaLinux 9
- Python: X.X.X
- Docker: X.X.X

【テスト結果】
✅ セットアップ検証: すべて正常
✅ システム起動: 正常
✅ Web UI: 正常動作
✅ API: 正常動作
✅ 検索機能: 正常動作
✅ 推奨事項生成: 正常動作

【パフォーマンス】
- 平均応答時間: XX秒
- Qdrantベクトル数: XXX件

【確認した機能】
- [ ] 基本検索
- [ ] コンテキスト付き検索
- [ ] 時間フィルタ
- [ ] ゼロヒット対応

【発見した問題】
（なければ「なし」）

【次のステップ】
- 運用員へのデモ
- フィードバック収集
```

---

**Phase 3 実装完了日**: 2025年11月10日
**Status**: ✅ 実装完了、テスト準備完了
