# DMARC Report Visualizer

DMARCレポートをSESで受信し、Lambdaで解析・Parquet変換してAmazon Managed Grafanaで可視化するシステム。

## アーキテクチャ

```
外部SMTP → SES → S3(受信) → Lambda(解析) → S3(Parquet) → Athena → Managed Grafana
```

## 前提条件

- Node.js 18+
- Docker（Lambda Layerビルド用）
- AWS CDK CLI (`npm install -g aws-cdk`)
- CDKブートストラップ済みのAWSアカウント
- IAM Identity Center有効化済み

## セットアップ

```bash
# 依存インストール
npm install

# Lambda Layerビルド（arm64向け、マルチプラットフォーム対応）
cd layer
docker buildx build --platform linux/arm64 -t dmarc-layer .
docker run --rm --platform linux/arm64 -v "$(pwd):/out" dmarc-layer \
  bash -c "cp -r /opt/python /out/python"
cd ..
```

## デプロイ

### 必須パラメータ

| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `receiveDomain` | SES受信ドメイン | `dmarc.example.com` |

### オプションパラメータ

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `glacierTransitionDays` | Glacier移行日数 | 395（約13ヶ月） |
| `expirationDays` | オブジェクト削除日数 | 760（約25ヶ月） |

### デプロイコマンド

```bash
npx cdk deploy -c receiveDomain=dmarc.example.com
```

カスタムライフサイクルを指定する場合:

```bash
npx cdk deploy \
  -c receiveDomain=dmarc.example.com \
  -c glacierTransitionDays=180 \
  -c expirationDays=365
```

## デプロイ後の手動手順

### 1. MXレコード設定

受信ドメインのDNSに以下を追加:

```
受信ドメイン.  MX  10 inbound-smtp.<region>.amazonaws.com.
```

### 2. DMARCレコード更新

監視対象ドメインのDNSに`rua`を追加:

```
_dmarc.example.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@<receiveDomain>"
```

### 3. SES Receipt Rule Set有効化

新規アカウントの場合、SESコンソールで `DmarcReceiptRuleSet` をアクティブに設定。

### 4. IAM Identity Centerユーザー割り当て

Grafana Workspaceにユーザーを割り当て:

1. Amazon Managed Grafanaコンソールを開く
2. `dmarc-dashboard` Workspaceを選択
3. 「Assign new user or group」でユーザーを追加（Editor権限）

## ダッシュボード

デプロイ後、Grafanaダッシュボードには以下のパネルが含まれます:

- **Daily DMARC Results**: 日別のpass/fail推移
- **Top Source IPs**: 送信元IPごとの認証結果一覧
- **Reports by Organization**: レポート送信元組織別の統計
- **SPF Results Breakdown**: SPF認証結果の内訳
- **DKIM Results Breakdown**: DKIM認証結果の内訳

## プロジェクト構成

```
├── bin/app.ts                    # CDK Appエントリポイント
├── lib/
│   ├── dmarc-report-visualizer-stack.ts
│   └── constructs/              # Storage, Ingestion, Parser, Catalog, Visualization
├── lambda/
│   ├── parser/                  # DMARCレポートパーサー（Python）
│   └── dashboard-provisioner/   # Grafanaダッシュボードプロビジョナー
├── layer/                       # Lambda Layer（pyarrow, defusedxml）
└── grafana/                     # ダッシュボード・データソース定義JSON
```

## 技術スタック

- **IaC**: AWS CDK v2 (TypeScript)
- **Lambda**: Python 3.14 / arm64
- **データ**: S3 + Glue + Athena (Parquet/Snappy)
- **可視化**: Amazon Managed Grafana + IAM Identity Center
