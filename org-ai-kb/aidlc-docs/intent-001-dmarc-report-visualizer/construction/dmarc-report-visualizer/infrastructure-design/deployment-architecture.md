# Deployment Architecture

## アーキテクチャ図

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   AWS Account                        │
                    │                                                      │
┌──────────┐       │  ┌───────────┐    ┌────────────────────────┐        │
│ External │ SMTP  │  │    SES    │    │  S3 (receive bucket)   │        │
│  Mail    │──────►│  │ Receipt   │───►│  incoming/*.eml        │        │
│ Servers  │       │  │ Rule      │    │  [versioned, encrypted]│        │
└──────────┘       │  └───────────┘    └───────────┬────────────┘        │
                    │                               │ S3 Event             │
                    │                               ▼                      │
                    │                    ┌────────────────────┐            │
                    │                    │  Lambda (Parser)   │            │
                    │                    │  Python 3.12/arm64 │            │
                    │                    │  + Layer (pyarrow) │            │
                    │                    └─────┬────────┬─────┘            │
                    │                          │        │                   │
                    │                 success  │        │ failure           │
                    │                          ▼        ▼                   │
                    │  ┌────────────────────────┐  ┌─────────┐            │
                    │  │  S3 (athena bucket)    │  │   SQS   │            │
                    │  │  dmarc-reports/        │  │   DLQ   │            │
                    │  │  year=.../month=.../   │  └─────────┘            │
                    │  │  [lifecycle, encrypted]│                          │
                    │  └───────────┬────────────┘                          │
                    │              │                                        │
                    │              ▼                                        │
                    │  ┌─────────────────────┐                            │
                    │  │  Glue Data Catalog  │                            │
                    │  │  dmarc_reports DB   │                            │
                    │  │  + table definition │                            │
                    │  └──────────┬──────────┘                            │
                    │             │                                         │
                    │             ▼                                         │
                    │  ┌─────────────────────┐    ┌───────────────────┐   │
                    │  │      Athena         │    │  S3 (results)     │   │
                    │  │  dmarc-workgroup    │───►│  query results    │   │
                    │  └──────────┬──────────┘    └───────────────────┘   │
                    │             │                                         │
                    │             ▼                                         │
                    │  ┌─────────────────────────────┐                    │
                    │  │   Managed Grafana           │                    │
                    │  │   IAM Identity Center Auth  │◄── Engineers (5)   │
                    │  │   Dashboard (provisioned)   │                    │
                    │  └─────────────────────────────┘                    │
                    │                                                      │
                    └─────────────────────────────────────────────────────┘
```

## デプロイフロー

```
Developer workstation
    │
    │ cdk deploy -c receiveDomain=... -c identityCenterInstanceArn=...
    │
    ▼
CloudFormation Stack: DmarcReportVisualizerStack
    │
    ├── StorageConstruct      → S3 Buckets (3)
    ├── IngestionConstruct    → SES Receipt Rule Set + Rule
    ├── ParserConstruct       → Lambda + Layer + DLQ + IAM
    ├── CatalogConstruct      → Glue DB + Table + Athena Workgroup
    └── VisualizationConstruct→ Grafana Workspace + Custom Resource (dashboard)
```

## デプロイ後の手動手順

1. **MXレコード設定**: 受信ドメインのDNSに `10 inbound-smtp.<region>.amazonaws.com` を追加
2. **DMARCレコード更新**: 対象ドメインのDNSで `rua=mailto:dmarc@<receiveDomain>` を設定
3. **SES Receipt Rule Set有効化**: 新規アカウントの場合、SESコンソールでRule Setをアクティブ化
4. **IAM Identity Centerユーザー割り当て**: Grafana Workspaceにユーザーを割り当て

## プロジェクトディレクトリ構成

```
dmarc-report-visualzer/
├── bin/
│   └── app.ts                      # CDK App エントリポイント
├── lib/
│   ├── dmarc-report-visualizer-stack.ts  # メインスタック
│   ├── constructs/
│   │   ├── storage.ts              # StorageConstruct
│   │   ├── ingestion.ts            # IngestionConstruct
│   │   ├── parser.ts               # ParserConstruct
│   │   ├── catalog.ts              # CatalogConstruct
│   │   └── visualization.ts        # VisualizationConstruct
│   └── utils/
│       └── ulid.ts                 # ULID生成ユーティリティ
├── lambda/
│   ├── parser/
│   │   └── lambda_function.py      # DMARCレポートパーサー
│   └── dashboard-provisioner/
│       └── index.py                # Grafanaダッシュボードプロビジョナー
├── layer/
│   ├── Dockerfile                  # Lambda Layer ビルド用
│   └── requirements.txt            # pyarrow, defusedxml
├── grafana/
│   ├── dashboards/
│   │   └── dmarc-overview.json     # メインダッシュボード定義
│   └── datasources/
│       └── athena.json             # Athenaデータソース定義
├── cdk.json                        # CDK設定 + context
├── tsconfig.json
├── package.json
└── README.md
```
