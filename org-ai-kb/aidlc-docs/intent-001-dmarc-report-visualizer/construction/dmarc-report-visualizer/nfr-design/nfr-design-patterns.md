# NFR Design Patterns

## 1. セキュリティパターン

### 1.1 Defence in Depth（多層防御）

```
Layer 1: S3 Bucket Policy (HTTPS強制, パブリックアクセスブロック)
Layer 2: IAM Role (最小権限, リソースレベルポリシー)
Layer 3: Application (defusedxml, 入力バリデーション)
Layer 4: Encryption (SSE-S3, 転送中TLS)
```

### 1.2 Lambda IAMポリシー設計

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::<receive-bucket>/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<athena-bucket>/dmarc-reports/*"
    },
    {
      "Effect": "Allow",
      "Action": "sqs:SendMessage",
      "Resource": "<dlq-arn>"
    }
  ]
}
```

- CloudWatch Logs権限はCDK Lambda構成で自動付与
- ワイルドカードはバケット内パスのみ（バケットARN自体は固定）

### 1.3 S3バケットポリシーテンプレート

```json
{
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": ["<bucket-arn>", "<bucket-arn>/*"],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

## 2. 信頼性パターン

### 2.1 Dead Letter Queue パターン

```
S3 Event → Lambda (max retry: 2)
              ↓ failure
         SQS DLQ (retention: 14 days)
              ↓ manual
         運用者が調査・再処理
```

- Lambda の `maxEventAge`: 6時間（デフォルト）
- Lambda の `retryAttempts`: 2（S3イベントの非同期呼び出し）
- DLQ の `messageRetentionPeriod`: 14日

### 2.2 冪等性パターン

```
Input:  S3 key (unique per email)
Output: s3://<athena-bucket>/dmarc-reports/year=.../month=.../day=.../{report_id}.parquet
```

- 同一入力 → 同一出力パス → S3 PutObject上書き = 副作用なし
- report_idがXML内で一意であることに依存（RFC7489保証）

### 2.3 バージョニング（受信バケット）

- 受信メールの誤削除・上書き保護
- ライフサイクルルールで旧バージョンのexpiration設定（90日後に旧バージョン削除）

## 3. パフォーマンスパターン

### 3.1 Parquetカラムナパーティショニング

```
s3://<athena-bucket>/
  dmarc-reports/
    year=2026/
      month=01/
        day=15/
          <report_id>.parquet
```

- パーティションキー: `year`, `month`, `day`（Hive形式）
- Athenaクエリで `WHERE year='2026' AND month='06'` → 対象パーティションのみスキャン
- snappy圧縮でI/Oコスト削減

### 3.2 Lambda最適化

- arm64アーキテクチャ: 20%コスト削減、同等以上の性能
- 512MB: PyArrowのメモリ使用に十分（比例してCPU性能も向上）
- Lambda Layer: コールドスタート時のコード展開を最小化

## 4. ポータビリティパターン

### 4.1 CDKパラメータ設計

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| receiveDomain | string | Yes | — | SES受信ドメイン |
| identityCenterInstanceArn | string | Yes | — | IAM Identity Center ARN |
| glacierTransitionDays | number | No | 395 | Glacier移行日数 |
| expirationDays | number | No | 760 | オブジェクト削除日数 |

- CDK Context (`cdk.json` or `-c` フラグ) で渡す
- `receiveDomain` と `identityCenterInstanceArn` は未指定時にデプロイエラー（バリデーション）

### 4.2 ULID バケット命名

```
<logical-name>-<ulid>
例: dmarc-receive-01J5A3B7C2D4E5F6G7H8J9K0M
```

- ULIDはCDK Appのコンストラクション時に生成
- `cdk.json` に永続化し、同一スタックの再デプロイで変わらない
- 実装: CDKの `PhysicalName.GENERATE_IF_NEEDED` ではなく、明示的にULIDサフィックスを付与

## 5. 可観測性パターン

### 5.1 構造化ログ

```json
{
  "timestamp": "2026-06-03T02:00:00Z",
  "level": "INFO",
  "event": "dmarc.parquet.written",
  "request_id": "abc-123",
  "report_id": "google.com!example.com!1717372800!1717459200",
  "records_count": 42,
  "output_path": "s3://..."
}
```

- Python `logging.setLogRecordFactory` + JSON formatter
- CloudWatch Logs Insightsでクエリ可能

### 5.2 CloudWatch Logs保持

- Lambda関数ログ: 30日
- CDK `logRetention: RetentionDays.ONE_MONTH`
