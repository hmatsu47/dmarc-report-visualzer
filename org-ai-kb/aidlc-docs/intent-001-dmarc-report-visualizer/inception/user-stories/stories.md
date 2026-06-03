# User Stories

## メール受信・保管

### S-1: DMARCレポートメールの自動受信

As the SES受信システム, when 外部メールサーバーからDMARCレポートメールが送信される, it must 受信しS3バケットにRFC822形式で保管する.

**Acceptance Criteria:**
- DMARCレポートメール（Content-Typeにapplication/gzip, application/zip, text/xmlの添付を含む）がSES経由で受信される
- 受信メールがS3バケットの所定プレフィックス配下に保存される
- 受信ドメインはCDKパラメータで指定されたものが使用される

**Requirements:** FR-1, FR-2, FR-3

---

## メール解析・変換

### S-2: gzip圧縮レポートの解析

As the Lambda解析関数, when S3にgzip圧縮された添付ファイルを含むDMARCレポートメールが保管される, it must gzipを展開しXMLをパースしてParquet形式でS3に出力する.

**Acceptance Criteria:**
- S3 putイベントでLambda関数がトリガーされる
- MIMEパートからgzip添付ファイル（.gz）を抽出できる
- 展開後のXMLが正しくパースされる
- FR-7で定義した全フィールドがフラット化されたParquetファイルがAthena用バケットに出力される

**Requirements:** FR-4, FR-5, FR-6, FR-7, FR-8

---

### S-3: ZIP圧縮レポートの解析

As the Lambda解析関数, when S3にZIP圧縮された添付ファイルを含むDMARCレポートメールが保管される, it must ZIPを展開しXMLをパースしてParquet形式でS3に出力する.

**Acceptance Criteria:**
- ZIP形式（.zip）の添付ファイルを認識し展開できる
- ZIP内に複数XMLが含まれる場合、すべてを処理する
- 展開後のXMLが正しくパースされParquetに変換される

**Requirements:** FR-4, FR-5, FR-6, FR-7, FR-8, FR-9

---

### S-4: 非圧縮XMLレポートの解析

As the Lambda解析関数, when S3に非圧縮XMLとして添付されたDMARCレポートメールが保管される, it must XMLを直接パースしてParquet形式でS3に出力する.

**Acceptance Criteria:**
- text/xmlまたはapplication/xml形式の添付ファイルを認識できる
- 圧縮展開なしでXMLを直接パースできる
- Parquetファイルが正しく出力される

**Requirements:** FR-4, FR-5, FR-6, FR-7, FR-8

---

### S-5: 解析エラー時のリトライ

As the Lambda解析関数, when メール解析中にエラーが発生する, it must Dead Letter Queue（SQS）に失敗メッセージを送信しリトライ可能とする.

**Acceptance Criteria:**
- 不正なXML、破損したZIP/gzipなどでエラー発生時にDLQへメッセージが送られる
- CloudWatch Logsにエラー詳細が記録される
- DLQのメッセージから再処理が可能である

**Requirements:** NFR-8, NFR-9

---

## データカタログ・クエリ

### S-6: Glueテーブル自動作成

As the CDKデプロイシステム, when スタックがデプロイされる, it must Glue Data CatalogにDMARCレポート用テーブル定義を自動作成する.

**Acceptance Criteria:**
- デプロイ後にGlue Data CatalogにテーブルがFR-7のスキーマで作成されている
- パーティションキーがdate_range_begin（日付）で定義されている
- Athenaから即座にクエリ可能である

**Requirements:** FR-10, FR-11, FR-12

---

## 可視化

### S-7: ダッシュボードでのDMARC認証結果確認

As a メールインフラ管理者, I want Grafanaダッシュボードで日別のDMARC認証結果（pass/fail）の推移を確認したい, so that ドメインの認証状況の変化を素早く把握できる.

**Acceptance Criteria:**
- 日別のpass/fail件数が時系列グラフで表示される
- 期間フィルタで表示範囲を変更できる
- データが存在しない期間はギャップとして表示される

**Requirements:** FR-16

---

### S-8: 送信元IP別の認証結果確認

As a メールインフラ管理者, I want 送信元IPごとのDMARC認証結果を一覧で確認したい, so that 不正な送信元や設定不備のサーバーを特定できる.

**Acceptance Criteria:**
- 送信元IPごとにpass/fail/count が表形式で表示される
- ソートおよびフィルタが可能である
- 特定IPの詳細（SPF/DKIM個別結果）にドリルダウンできる

**Requirements:** FR-16

---

### S-9: ドメイン別レポート統計の確認

As a メールインフラ管理者, I want ドメイン別のレポート統計を確認したい, so that 複数ドメインを管理している場合に各ドメインの状況を比較できる.

**Acceptance Criteria:**
- レポート送信元組織（org_name）ごとの集計が表示される
- ドメインごとのpass率が可視化される

**Requirements:** FR-16

---

### S-10: SPF/DKIM個別結果の確認

As a メールインフラ管理者, I want SPFとDKIMの個別認証結果の内訳を確認したい, so that どの認証メカニズムに問題があるか切り分けできる.

**Acceptance Criteria:**
- SPF結果（pass/fail/softfail/neutral等）の内訳が円グラフまたは棒グラフで表示される
- DKIM結果の内訳が同様に表示される
- 時系列での推移も確認可能である

**Requirements:** FR-16

---

## IaC・デプロイ

### S-11: CDKによるワンコマンドデプロイ

As a メールインフラ管理者, I want `cdk deploy`の1コマンドで全リソースをデプロイしたい, so that 異なるAWSアカウントに容易に展開できる.

**Acceptance Criteria:**
- `cdk deploy --parameters ...` で必要なパラメータを渡してデプロイ完了する
- デプロイ後にSES受信ルール、S3バケット、Lambda、Glueテーブル、Grafana Workspaceが作成されている
- S3バケット名にULIDサフィックスが付与されている

**Requirements:** FR-17, FR-18, FR-19, FR-20

---

### S-12: データライフサイクル管理

As the S3ライフサイクルシステム, when Parquetデータが所定期間を経過する, it must パラメータで指定された期間に従いGlacier移行および削除を実行する.

**Acceptance Criteria:**
- デフォルト13ヶ月でS3 Glacier Flexible Retrievalに移行する
- デフォルト25ヶ月でオブジェクトが削除される
- 移行・削除期間はCDKパラメータで変更可能である

**Requirements:** NFR-10

---

## セキュリティ

### S-13: XMLパーサーのXXE攻撃防止

As the Lambda解析関数, when DMARCレポートXMLをパースする, it must 外部エンティティの解決を無効化しXXE攻撃を防止する.

**Acceptance Criteria:**
- 外部エンティティ参照を含む悪意あるXMLが処理されても外部リソースへのアクセスが発生しない
- 不正なXMLは安全に拒否されDLQに送られる

**Requirements:** NFR-6

---

### S-14: S3バケットのアクセス制御

As the CDKデプロイシステム, when S3バケットを作成する, it must パブリックアクセスを完全にブロックしサーバーサイド暗号化を有効化する.

**Acceptance Criteria:**
- BlockPublicAccess が全項目trueで設定される
- SSE-S3またはSSE-KMSによるデフォルト暗号化が有効である
- バケットポリシーでHTTPS通信のみ許可する

**Requirements:** NFR-3, NFR-4

---

### S-15: ダッシュボードJSONのリポジトリ管理

As a メールインフラ管理者, I want GrafanaダッシュボードのJSONをGitリポジトリで管理したい, so that ダッシュボードの変更履歴を追跡しデプロイを再現可能にできる.

**Acceptance Criteria:**
- ダッシュボードJSON定義がリポジトリ内に格納されている
- CDKデプロイ時にGrafana APIを通じてダッシュボードがプロビジョニングされる
- ダッシュボード変更はリポジトリの変更 → 再デプロイで反映される

**Requirements:** FR-15
