# Tech Stack Decisions

## IaC

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Infrastructure as Code | AWS CDK (TypeScript) | 型安全、L2コンストラクト豊富、要件FR-17 |
| CDK Version | v2 (aws-cdk-lib) | 最新安定版、モノパッケージ |

## Runtime

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Lambda Runtime | Python 3.12 | 参考コードとの一貫性、メール/XMLライブラリ充実 |
| Lambda Architecture | arm64 | コスト20%削減、Python完全対応 |
| Lambda Memory | 512MB | Parquet変換のPyArrowメモリ使用に十分 |
| Lambda Timeout | 60秒 | NFR-1（30秒）に対しマージン |

## Data Processing Libraries

| Library | Purpose | Rationale |
|---------|---------|-----------|
| defusedxml | XMLパース | XXE攻撃防止（SEC-3） |
| pyarrow | Parquet生成 | Apache標準、Lambda Layer対応 |
| email (stdlib) | MIME解析 | 標準ライブラリ、追加依存なし |
| gzip (stdlib) | gzip展開 | 標準ライブラリ |
| zipfile (stdlib) | ZIP展開 | 標準ライブラリ |

## Storage

| Layer | Choice | Rationale |
|-------|--------|-----------|
| メール保管 | S3 Standard | 低コスト、SES直接連携 |
| Parquet保管 | S3 Standard → Glacier | ライフサイクルで自動移行（OPS-2） |
| データカタログ | AWS Glue Data Catalog | Athena統合、CDK対応 |
| クエリエンジン | Amazon Athena | サーバーレス、Parquet直接クエリ |

## Visualization

| Layer | Choice | Rationale |
|-------|--------|-----------|
| ダッシュボード | Amazon Managed Grafana | Identity Center直接統合、Athenaプラグイン |
| 認証 | IAM Identity Center (SSO) | エンジニア向け、既存インフラ活用 |
| ダッシュボード管理 | Grafana HTTP API + JSON | IaC化、リポジトリ管理、再現可能 |

## Messaging

| Layer | Choice | Rationale |
|-------|--------|-----------|
| イベントトリガー | S3 Event Notification → Lambda | シンプル、追加サービス不要 |
| DLQ | SQS Standard Queue | Lambda DLQ統合、14日保持 |

## Packaging

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Lambda Dependency | Lambda Layer (pyarrow, defusedxml) | デプロイサイズ最適化、共有可能 |
| Lambda Code | インラインバンドル（CDK PythonFunction or asset） | CDK管理、バージョニング自動 |

## Decision Records

### DR-1: SSE-S3 vs SSE-KMS

**Decision**: SSE-S3を採用
**Rationale**: DMARCレポートはInternal分類データでありKMS管理の追加コスト・複雑性は不要。KMS APIコール料金も回避。

### DR-2: S3 Event Notification vs EventBridge

**Decision**: S3 Event Notificationを採用
**Rationale**: 単一Lambda宛のシンプルなトリガー。EventBridgeの柔軟性（ルーティング、フィルタ）は不要。

### DR-3: Parquet vs JSON（Athena用）

**Decision**: Parquetを採用
**Rationale**: カラムナ形式でAthenaスキャンコスト削減、snappy圧縮でストレージ効率化。参考コードのJSON出力から変更。

### DR-4: Lambda Layer vs Container Image

**Decision**: Lambda Layerを採用
**Rationale**: pyarrow + defusedxml で ~60MB。コンテナイメージの管理オーバーヘッド不要。
