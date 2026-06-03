# Component Methods

## EmailReceiver

### receiveEmail

- **Inputs**: SMTP message（外部メールサーバーから）
- **Outputs**: S3 object（RFC822形式、受信バケット内）
- **Preconditions**: SES Receipt Ruleが有効、受信ドメインのMXレコードがSESを指している
- **Postconditions**: メールオブジェクトがS3に保存され、S3イベント通知が発行される

## DmarcReportParser

### parseEmail

- **Inputs**: S3Event（バケット名、オブジェクトキー）
- **Outputs**: なし（副作用としてParquetファイルを出力）
- **Preconditions**: S3オブジェクトがRFC822形式のメールである
- **Postconditions**: DMARCレポート添付ファイルが解析され、ParquetファイルがAthena用バケットに出力されている

### extractAttachments

- **Inputs**: email.Message（パース済みメールオブジェクト）
- **Outputs**: List[Attachment]（content_type, filename, content）
- **Preconditions**: メールがMIMEマルチパート構造を持つ
- **Postconditions**: DMARCレポートに該当する添付ファイルが抽出されている

### decompressContent

- **Inputs**: Attachment（content_type, raw_bytes）
- **Outputs**: bytes（展開後のXMLコンテンツ）
- **Preconditions**: content_typeがgzip, zip, またはxml
- **Postconditions**: XMLバイト列が取得されている。ZIP内の複数ファイルはすべて返される

### parseXmlToRecords

- **Inputs**: bytes（XMLコンテンツ）
- **Outputs**: List[DmarcRecord]（フラット化されたレコードリスト）
- **Preconditions**: XMLがDMARC aggregate report schema（RFC7489）に準拠
- **Postconditions**: メタデータ・ポリシー・レコードがフラット化されたリストとして返される。XXE攻撃は無効化されている

### writeParquet

- **Inputs**: List[DmarcRecord], 出力先S3パス
- **Outputs**: S3 object（Parquet形式）
- **Preconditions**: レコードリストが空でない
- **Postconditions**: Parquetファイルが日付パーティションに従ったパスに書き込まれている

## DataCatalog

### defineTable

- **Inputs**: テーブル名、スキーマ定義、パーティションキー、S3ロケーション
- **Outputs**: Glue Table（CDKリソースとしてデプロイ時に作成）
- **Preconditions**: Glue Databaseが存在する
- **Postconditions**: Athenaからクエリ可能なテーブル定義が存在する

## Visualization

### provisionDashboard

- **Inputs**: ダッシュボードJSON定義、Grafana Workspace URL、APIキー
- **Outputs**: デプロイ済みダッシュボード
- **Preconditions**: Grafana Workspaceが稼働中、Athenaデータソースが設定済み
- **Postconditions**: ダッシュボードがGrafana上で閲覧可能

### queryAthena

- **Inputs**: SQLクエリ（Grafanaパネルから発行）
- **Outputs**: クエリ結果（テーブル/時系列データ）
- **Preconditions**: Glueテーブルが定義済み、Parquetデータが存在する
- **Postconditions**: クエリ結果がGrafanaパネルに表示される

## StorageManager

### createBucket

- **Inputs**: バケット名プレフィックス、暗号化設定、ライフサイクルパラメータ
- **Outputs**: S3 Bucket（ULIDサフィックス付き）
- **Preconditions**: なし
- **Postconditions**: パブリックアクセスブロック、暗号化、ライフサイクルルールが設定されたバケットが作成される
