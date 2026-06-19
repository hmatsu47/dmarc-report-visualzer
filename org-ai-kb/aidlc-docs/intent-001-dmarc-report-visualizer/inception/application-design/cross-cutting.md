# Cross-Cutting Concerns

## Error Format

```
{
  "error_code": "<COMPONENT>_<ERROR_TYPE>",
  "message": "人が読める説明",
  "details": { ... },
  "timestamp": "ISO8601",
  "request_id": "Lambda request ID or trace ID"
}
```

エラーコード体系:
- `PARSER_INVALID_MIME` — MIME構造の解析失敗
- `PARSER_DECOMPRESS_FAILED` — gzip/ZIP展開失敗
- `PARSER_INVALID_XML` — XMLパースエラー（XXE含む）
- `PARSER_SCHEMA_MISMATCH` — DMARCスキーマ不適合
- `PARSER_WRITE_FAILED` — Parquet書き込み失敗

## Authorisation Model

- **認証**: IAM Identity Center（Grafana Workspace）
- **認可**: ユーザーはAdmin権限で割り当て（データソース設定・ダッシュボード編集に必要）
- **Service Account**: ADMIN権限（ダッシュボードプロビジョニング用Custom Resourceが使用）
- **内部サービス間**: IAMロールベース（最小権限原則）
  - Lambda → S3: GetObject（受信バケット）、PutObject（Athenaバケット）
  - Grafana → Athena: athena:StartQueryExecution, athena:GetQueryResults
  - Athena → S3: GetObject（Athenaバケット）
  - Athena → Glue: GetTable, GetPartitions

## Logging Taxonomy

| Event | Severity | 出力タイミング |
|-------|----------|--------------|
| `dmarc.email.received` | INFO | S3イベント受信時 |
| `dmarc.attachment.extracted` | INFO | 添付ファイル抽出成功時 |
| `dmarc.decompress.success` | INFO | 展開成功時 |
| `dmarc.xml.parsed` | INFO | XMLパース成功時 |
| `dmarc.parquet.written` | INFO | Parquet出力成功時 |
| `dmarc.parse.error` | ERROR | 解析失敗時（DLQ送信前） |
| `dmarc.decompress.error` | ERROR | 展開失敗時 |
| `dmarc.xml.xxe_blocked` | WARN | XXE攻撃検知時 |
| `dmarc.attachment.skipped` | WARN | DMARC以外の添付をスキップ時 |

ログは構造化JSON形式でCloudWatch Logsに出力する。

## Validation Approach

- **入力バリデーション**: DmarcReportParser内で実施
  - MIMEパート: Content-Typeチェック
  - 圧縮ファイル: マジックバイト検証
  - XML: 外部エンティティ無効化（defusedxml使用）、スキーマ検証
- **CDKパラメータ**: CDKレベルでバリデーション（型チェック、許容値範囲）
- **Grafanaクエリ**: Athena側のスキーマ制約で保護
