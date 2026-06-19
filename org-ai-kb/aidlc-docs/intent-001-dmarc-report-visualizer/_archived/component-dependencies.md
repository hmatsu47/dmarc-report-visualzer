# Component Dependencies

## Dependency Matrix

| From | To | Pattern | Rationale |
|------|-----|---------|-----------|
| EmailReceiver | StorageManager | async event（S3 Put） | SES Receipt RuleがS3バケットにメールを保管する |
| DmarcReportParser | StorageManager | sync call（S3 Get/Put） | 受信バケットからメール取得、Athenaバケットへ出力 |
| DmarcReportParser | EmailReceiver | async event（S3 Event Notification） | S3 putイベントがLambdaをトリガーする |
| Visualization | DataCatalog | sync call（Athena Query） | GrafanaダッシュボードがAthena経由でデータをクエリする |
| DataCatalog | StorageManager | 設定参照（S3 Location） | Glueテーブルのデータソースとしてパーティション用S3パスを参照 |

## データフロー

```
外部メールサーバー
    ↓ SMTP
EmailReceiver (SES)
    ↓ S3 Put (RFC822)
StorageManager (受信バケット)
    ↓ S3 Event Notification
DmarcReportParser (Lambda)
    ↓ S3 Put (Parquet)
StorageManager (Athenaバケット)
    ↓ Athena Query
DataCatalog (Glue Table) ← Visualization (Grafana)
```

## Circular Dependencies

なし
