# Services

## DmarcIngestionService

- **Purpose**: DMARCレポートメールの受信からParquet変換までのEnd-to-Endパイプラインを統括する
- **Components used**: EmailReceiver, DmarcReportParser, StorageManager
- **Operations**:
  1. SESがメールを受信し受信バケットに保管（EmailReceiver → StorageManager）
  2. S3イベントがLambdaをトリガー（StorageManager → DmarcReportParser）
  3. Lambdaがメール解析・Parquet変換・出力（DmarcReportParser → StorageManager）
- **Stories addressed**: S-1, S-2, S-3, S-4, S-5

## DmarcVisualizationService

- **Purpose**: 蓄積されたDMARCレポートデータのクエリと可視化を統括する
- **Components used**: DataCatalog, Visualization, StorageManager
- **Operations**:
  1. Grafanaダッシュボードからクエリ発行（Visualization → DataCatalog）
  2. AthenaがS3のParquetデータをスキャン（DataCatalog → StorageManager）
  3. 結果をダッシュボードに表示（DataCatalog → Visualization）
- **Stories addressed**: S-7, S-8, S-9, S-10

## InfraProvisioningService

- **Purpose**: CDKによる全リソースのプロビジョニングとライフサイクル管理を統括する
- **Components used**: StorageManager, EmailReceiver, DmarcReportParser, DataCatalog, Visualization
- **Operations**:
  1. S3バケット作成（ULIDサフィックス、暗号化、ライフサイクル）
  2. SES Receipt Rule作成
  3. Lambda関数デプロイ（DLQ付き）
  4. Glueテーブル定義
  5. Grafana Workspace作成・ダッシュボードプロビジョニング
- **Stories addressed**: S-6, S-11, S-12, S-13, S-14, S-15
