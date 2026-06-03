# Logical Components

## CDKスタック構成

単一CDKアプリ内で論理的にConstructを分割する:

```
DmarcReportVisualizerApp (App)
  └── DmarcReportVisualizerStack (Stack)
        ├── StorageConstruct
        │     ├── receiveBucket (S3)
        │     ├── athenaBucket (S3)
        │     └── lifecycleRules
        ├── IngestionConstruct
        │     ├── sesReceiptRuleSet (SES)
        │     ├── sesReceiptRule (SES)
        │     └── s3EventNotification config
        ├── ParserConstruct
        │     ├── parserFunction (Lambda)
        │     ├── parserLayer (Lambda Layer: pyarrow, defusedxml)
        │     ├── deadLetterQueue (SQS)
        │     └── parserRole (IAM Role)
        ├── CatalogConstruct
        │     ├── glueDatabase (Glue)
        │     ├── glueTable (Glue)
        │     └── athenaWorkgroup (Athena)
        └── VisualizationConstruct
              ├── grafanaWorkspace (Managed Grafana)
              ├── grafanaRole (IAM Role)
              └── dashboardProvisioner (Custom Resource or post-deploy script)
```

## Construct間の依存関係

| From | To | 参照内容 |
|------|-----|---------|
| IngestionConstruct | StorageConstruct | receiveBucket ARN |
| ParserConstruct | StorageConstruct | receiveBucket ARN, athenaBucket ARN |
| ParserConstruct | IngestionConstruct | S3 Event Notification source |
| CatalogConstruct | StorageConstruct | athenaBucket S3 location |
| VisualizationConstruct | CatalogConstruct | Athena workgroup, Glue database |

## Lambda Layer構成

```
layer/
  python/
    lib/
      python3.12/
        site-packages/
          pyarrow/
          defusedxml/
```

- ビルド: Docker (amazonlinux:2023 + pip install) でarm64向けにコンパイル
- サイズ見積もり: ~60MB (pyarrow ~55MB + defusedxml ~100KB)
- CDK: `lambda.LayerVersion` で管理

## Grafanaダッシュボードプロビジョニング

### 方式: CDK Custom Resource

```
CustomResource (CR_GRAFANA_DASHBOARD)
  ├── onCreate: Grafana HTTP API POST /api/dashboards/db
  ├── onUpdate: Grafana HTTP API POST /api/dashboards/db (overwrite: true)
  └── onDelete: Grafana HTTP API DELETE /api/dashboards/uid/<uid>
```

- Custom ResourceのLambdaがGrafana API keyを使用してダッシュボードをプロビジョニング
- API keyはGrafana WorkspaceのService Account Token（CDKで作成）
- ダッシュボードJSONは`grafana/dashboards/`ディレクトリに格納

### リポジトリ内ダッシュボード配置

```
grafana/
  dashboards/
    dmarc-overview.json      # メインダッシュボード
  datasources/
    athena.json              # Athenaデータソース定義
```
