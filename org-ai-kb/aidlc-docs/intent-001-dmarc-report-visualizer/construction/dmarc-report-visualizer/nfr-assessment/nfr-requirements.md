# NFR Requirements

## Performance

### PERF-1: Lambda処理時間

- **Target**: 単一メール処理 ≤ 30秒
- **Rationale**: 一般的なDMARCレポート（数百〜数千レコード）は数秒で処理可能。30秒はZIP内に大量XMLを含む異常ケースへのバッファ
- **Measurement**: Lambda Duration メトリクス（p99）
- **Configuration**: Lambda timeout = 60秒（マージン含む）、memory = 512MB

### PERF-2: Athenaクエリ応答

- **Target**: 1ヶ月分データ ≤ 10秒
- **Rationale**: Grafanaダッシュボードのインタラクティブ操作に十分な応答速度
- **Measurement**: Athena QueryExecutionTime
- **Configuration**: Parquet + snappy圧縮 + 日付パーティションでスキャン量を最小化

### PERF-3: データ量見積もり

- **想定**: 1日50通 × 平均50レコード/レポート = 2,500行/日
- **月間**: ~75,000行、Parquetサイズ ~5MB/月
- **年間**: ~60MB（Athenaスキャン観点で極めて軽量）

## Security

### SEC-1: S3暗号化

- **Target**: 全S3バケットでサーバーサイド暗号化を強制
- **Implementation**: SSE-S3（aws:kms不要 — コスト最適化）
- **Enforcement**: BucketPolicy で `s3:PutObject` に `x-amz-server-side-encryption` ヘッダー必須

### SEC-2: パブリックアクセスブロック

- **Target**: 全S3バケットでBlockPublicAccessを全項目true
- **Implementation**: CDK `BlockPublicAccess.BLOCK_ALL`

### SEC-3: XXE防止

- **Target**: XMLパース時の外部エンティティ解決を完全無効化
- **Implementation**: `defusedxml` ライブラリ使用（標準`xml.etree.ElementTree`を置換）
- **Verification**: 悪意あるXMLテストケースで外部アクセスが発生しないことを確認

### SEC-4: Lambda IAM最小権限

- **Target**: Lambda関数のIAMロールは必要最小限のアクションのみ許可
- **Permissions**:
  - `s3:GetObject` — 受信バケット（指定プレフィックス）
  - `s3:PutObject` — Athenaバケット（dmarc-reports/プレフィックス）
  - `sqs:SendMessage` — DLQのみ
  - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` — CloudWatch Logs

### SEC-5: HTTPS強制

- **Target**: S3バケットへのアクセスはHTTPS（TLS）のみ許可
- **Implementation**: BucketPolicy で `aws:SecureTransport: false` を拒否

### SEC-6: Grafana認証

- **Target**: IAM Identity Center認証必須、匿名アクセス不可
- **Implementation**: `CfnWorkspace` の `authenticationProviders: ["AWS_SSO"]`

## Reliability

### REL-1: Lambda DLQ

- **Target**: 処理失敗メッセージはDLQに送達され、手動再処理可能
- **Implementation**: SQS Standard Queue をLambdaの Dead Letter Queue に設定
- **Retention**: DLQメッセージ保持期間 = 14日

### REL-2: Lambda同時実行制御

- **Target**: S3イベントの大量同時発生（初回一括取り込み等）時にスロットルしない
- **Implementation**: Reserved Concurrency は設定しない（アカウントデフォルト上限に依存）
- **Rationale**: 通常トラフィックは数十通/日で問題にならない

### REL-3: S3バージョニング

- **Target**: 受信メールバケットはバージョニング有効（誤削除対策）
- **Implementation**: CDK `versioned: true`

## Operability

### OPS-1: CloudWatch Logs

- **Target**: Lambda実行ログは構造化JSONでCloudWatch Logsに出力
- **Retention**: 30日（コスト最適化）
- **Implementation**: Python `logging` + JSON formatter

### OPS-2: ライフサイクルポリシー

- **Target**: Parquetデータの自動アーカイブ・削除
- **Implementation**:
  - Glacier Flexible Retrieval移行: デフォルト13ヶ月（パラメータ`glacierTransitionDays`、デフォルト395日）
  - 削除: デフォルト25ヶ月（パラメータ`expirationDays`、デフォルト760日）
- **Scope**: Athenaバケットのみ（受信メールバケットは保持）

## Portability

### PORT-1: マルチアカウントデプロイ

- **Target**: 任意のAWSアカウント・リージョンにデプロイ可能
- **Implementation**: 環境依存値はすべてCDK context / CfnParameter で外部化
- **Parameters**:
  - `receiveDomain` — SES受信ドメイン（必須）
  - `glacierTransitionDays` — Glacier移行日数（デフォルト395）
  - `expirationDays` — 削除日数（デフォルト760）
