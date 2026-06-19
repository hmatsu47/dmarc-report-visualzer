# Event Catalog

## s3:ObjectCreated (受信メール)

- **Purpose**: DMARCレポートメールがS3に保管されたことを通知する
- **Producer**: EmailReceiver（SES Receipt Rule → S3）
- **Consumers**: DmarcReportParser（Lambda関数）
- **Payload**:
  ```
  {
    "bucket": string,
    "key": string,
    "size": integer,
    "eventTime": timestamp
  }
  ```
- **Delivery semantics**: at-least-once（S3 Event Notification）
- **Ordering requirements**: なし（各メールは独立処理）

## DLQ Message (解析失敗)

- **Purpose**: Lambda関数の処理失敗をリトライ可能な形で保持する
- **Producer**: DmarcReportParser（Lambda DLQ機構）
- **Consumers**: 運用者（手動調査・再処理）
- **Payload**:
  ```
  {
    "source_bucket": string,
    "source_key": string,
    "error_code": string,
    "error_message": string,
    "timestamp": timestamp,
    "attempt_count": integer
  }
  ```
- **Delivery semantics**: at-least-once（SQS Standard）
- **Ordering requirements**: なし
