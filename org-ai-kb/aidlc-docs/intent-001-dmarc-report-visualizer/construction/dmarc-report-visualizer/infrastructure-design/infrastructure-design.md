# Infrastructure Design

## AWSリソース一覧

| # | Resource | Service | Construct | Purpose |
|---|----------|---------|-----------|---------|
| 1 | dmarc-receive-{ulid} | S3 Bucket | StorageConstruct | 受信メール保管 |
| 2 | dmarc-athena-{ulid} | S3 Bucket | StorageConstruct | Parquetデータ保管 |
| 3 | dmarc-athena-results-{ulid} | S3 Bucket | StorageConstruct | Athenaクエリ結果保管 |
| 4 | DmarcReceiptRuleSet | SES Receipt Rule Set | IngestionConstruct | 受信ルール管理 |
| 5 | DmarcReceiptRule | SES Receipt Rule | IngestionConstruct | ドメイン受信→S3 |
| 6 | dmarc-report-parser | Lambda Function | ParserConstruct | メール解析・Parquet変換 |
| 7 | dmarc-parser-layer | Lambda Layer | ParserConstruct | pyarrow + defusedxml |
| 8 | DmarcParserRole | IAM Role | ParserConstruct | Lambda実行ロール |
| 9 | DmarcDLQ | SQS Queue | ParserConstruct | 処理失敗メッセージ |
| 10 | dmarc_reports | Glue Database | CatalogConstruct | データカタログDB |
| 11 | dmarc_aggregate_reports | Glue Table | CatalogConstruct | レポートテーブル定義 |
| 12 | DmarcAthenaWorkgroup | Athena Workgroup | CatalogConstruct | クエリ実行環境 |
| 13 | DmarcGrafanaWorkspace | Managed Grafana Workspace | VisualizationConstruct | ダッシュボード |
| 14 | DmarcGrafanaRole | IAM Role | VisualizationConstruct | Grafana→Athena権限 |
| 15 | DashboardProvisioner | Custom Resource (Lambda) | VisualizationConstruct | ダッシュボードデプロイ |

## リソース詳細設定

### S3 Buckets (StorageConstruct)

#### dmarc-receive-{ulid}

```
- Versioned: true
- BlockPublicAccess: BLOCK_ALL
- Encryption: SSE-S3
- RemovalPolicy: RETAIN
- BucketPolicy: DenyInsecureTransport
- EventNotification: s3:ObjectCreated:* → Lambda (dmarc-report-parser)
- Prefix filter: (none — all objects trigger)
```

#### dmarc-athena-{ulid}

```
- Versioned: false
- BlockPublicAccess: BLOCK_ALL
- Encryption: SSE-S3
- RemovalPolicy: RETAIN
- BucketPolicy: DenyInsecureTransport
- LifecycleRules:
  - Transition to GLACIER: {glacierTransitionDays} days (default 395)
  - Expiration: {expirationDays} days (default 760)
  - Scope: prefix "dmarc-reports/"
```

#### dmarc-athena-results-{ulid}

```
- Versioned: false
- BlockPublicAccess: BLOCK_ALL
- Encryption: SSE-S3
- RemovalPolicy: DESTROY (クエリ結果は一時的)
- LifecycleRules:
  - Expiration: 7 days
```

### SES (IngestionConstruct)

```
ReceiptRuleSet:
  - Name: DmarcReceiptRuleSet
  - Active: true (手動でアクティブ化が必要な場合あり)

ReceiptRule:
  - Name: DmarcReceiptRule
  - Recipients: [{receiveDomain}]
  - Actions:
    - S3Action:
        Bucket: dmarc-receive-{ulid}
        ObjectKeyPrefix: "incoming/"
  - ScanEnabled: true (spam/virus scan)
```

### Lambda (ParserConstruct)

#### dmarc-report-parser

```
- Runtime: python3.12
- Architecture: arm64
- Memory: 512 MB
- Timeout: 60 seconds
- Handler: lambda_function.handler
- Layers: [dmarc-parser-layer]
- DeadLetterQueue: DmarcDLQ
- RetryAttempts: 2
- MaxEventAge: 6 hours
- LogRetention: 30 days
- Environment:
    ATHENA_BUCKET: (athenaBucket.bucketName)
    OUTPUT_PREFIX: "dmarc-reports"
- Trigger: S3 Event (receiveBucket, s3:ObjectCreated:*, prefix: "incoming/")
```

#### dmarc-parser-layer

```
- CompatibleRuntimes: [python3.12]
- CompatibleArchitectures: [arm64]
- Contents: pyarrow, defusedxml
- Build: Docker (amazonlinux:2023, pip install --target)
```

### SQS (ParserConstruct)

#### DmarcDLQ

```
- MessageRetentionPeriod: 14 days (1209600 seconds)
- VisibilityTimeout: 60 seconds
- Encryption: SQS managed (SSE-SQS)
```

### Glue (CatalogConstruct)

#### Database: dmarc_reports

```
- Name: dmarc_reports
- Description: DMARC aggregate report data catalog
```

#### Table: dmarc_aggregate_reports

```
- DatabaseName: dmarc_reports
- TableType: EXTERNAL_TABLE
- StorageDescriptor:
    Location: s3://dmarc-athena-{ulid}/dmarc-reports/
    InputFormat: org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat
    OutputFormat: org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat
    SerdeInfo:
      SerializationLibrary: org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe
    Columns: (FR-7 全フィールド)
- PartitionKeys:
    - {Name: year, Type: string}
    - {Name: month, Type: string}
    - {Name: day, Type: string}
```

### Athena (CatalogConstruct)

#### DmarcAthenaWorkgroup

```
- Name: dmarc-workgroup
- OutputLocation: s3://dmarc-athena-results-{ulid}/
- EnforceWorkGroupConfiguration: true
- PublishCloudWatchMetricsEnabled: true
- BytesScannedCutoffPerQuery: 1 GB
```

### Managed Grafana (VisualizationConstruct)

#### DmarcGrafanaWorkspace

```
- Name: dmarc-dashboard
- AuthenticationProviders: [AWS_SSO]
- AccountAccessType: CURRENT_ACCOUNT
- PermissionType: SERVICE_MANAGED
- DataSources: [ATHENA]
- RoleArn: DmarcGrafanaRole
```

#### DmarcGrafanaRole

```
- AssumeRolePolicy: grafana.amazonaws.com
- Policies:
  - athena:StartQueryExecution
  - athena:GetQueryExecution
  - athena:GetQueryResults
  - athena:StopQueryExecution
  - athena:GetWorkGroup
  - s3:GetObject, s3:ListBucket (athena-results bucket)
  - s3:GetObject, s3:ListBucket (athena bucket, dmarc-reports/ prefix)
  - s3:PutObject, s3:GetBucketLocation (athena-results bucket)
  - glue:GetTable, glue:GetPartitions, glue:GetDatabase
```

#### DashboardProvisioner (Custom Resource)

```
- Runtime: python3.12
- Timeout: 120 seconds
- Purpose: Grafana HTTP API呼び出し (dashboard + datasource provisioning)
- Inputs:
  - workspaceId (from GrafanaWorkspace)
  - dashboardJson (from grafana/dashboards/)
  - datasourceJson (from grafana/datasources/)
- Dependencies: GrafanaWorkspace must be ACTIVE
```

## IAM Policy Summary

### DmarcParserRole

```
Allow s3:GetObject          on arn:aws:s3:::dmarc-receive-{ulid}/*
Allow s3:PutObject          on arn:aws:s3:::dmarc-athena-{ulid}/dmarc-reports/*
Allow sqs:SendMessage       on DmarcDLQ ARN
Allow logs:*                on /aws/lambda/dmarc-report-parser (auto-granted by CDK)
```

### DmarcGrafanaRole

```
Allow athena:*Query*        on DmarcAthenaWorkgroup
Allow s3:GetObject,ListBucket on dmarc-athena-{ulid}
Allow s3:*                  on dmarc-athena-results-{ulid}
Allow glue:Get*             on dmarc_reports database and tables
```
