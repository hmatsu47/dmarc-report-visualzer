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

### 1. SESドメイン検証

SESでメールを受信するには、受信ドメインの所有権を検証する必要があります。

1. SESコンソールで「Verified identities」→「Create identity」を選択
2. 「Domain」を選択し、受信ドメイン（例: `dmarc.example.com`）を入力
3. 「Advanced DKIM settings」で「Easy DKIM」を選択（鍵長は「RSA_2048_BIT」推奨）
4. DNSの管理方法に応じて以下のいずれかを選択:
   - **同一アカウントのRoute 53でホストしている場合**: 「Publish DNS records to Route 53」にチェックを入れる
   - **別アカウントのRoute 53または外部DNSを使用する場合**: チェックを入れずに進む
5. 「Create identity」をクリック後、DKIMの3つのCNAMEレコードを登録:
   - **同一アカウントのRoute 53の場合**: 自動登録される（対応不要）
   - **別アカウントのRoute 53の場合**: SESコンソールの「Authentication」タブに表示される3つのCNAMEレコードを、該当アカウントのRoute 53ホストゾーンに手動で追加する
   - **Route 53以外のDNSの場合**: 表示される3つのCNAMEレコードを、利用中のDNSサービスの管理画面で手動で追加する

※ ステータスが「Verified」になるまで数分〜最大72時間かかる場合があります。

### 2. MXレコード設定

受信ドメインのDNSに以下を追加:

```
受信ドメイン.  MX  10 inbound-smtp.<region>.amazonaws.com.
```

### 3. DMARCレコード更新

監視対象ドメインのDNSに`rua`を追加:

```
_dmarc.example.com.  TXT  "v=DMARC1; p=none; rua=mailto:dmarc@<receiveDomain>"
```

### 4. SES Receipt Rule Set有効化

新規アカウントの場合、SESコンソールで `DmarcReceiptRuleSet` をアクティブに設定。

### 5. IAM Identity Centerユーザー割り当て

Grafana Workspaceにユーザーを割り当て:

1. Amazon Managed Grafanaコンソールを開く
2. `dmarc-dashboard` Workspaceを選択
3. 「Assign new user or group」でユーザーを追加（Admin権限）

> **注意**: ワークスペースのバージョンアップ等により、ユーザーの権限が「閲覧者（Viewer）」にリセットされる場合があります。データソース設定やダッシュボードの編集ができない場合は、Managed Grafanaコンソールでユーザーの権限を「Admin」に変更してください。

### 6. データソースとダッシュボードの有効化

初回デプロイ後、Grafanaダッシュボードでデータソースを有効化する必要があります。

1. Grafana Workspaceにログイン
2. 左メニュー → **Connections** → **Data sources** を開く
3. 「Amazon Athena - DMARC」をクリック
4. Athena Detailsセクションで **Workgroup** に `dmarc-workgroup` を選択
5. 「Save & Test」をクリックし、「Data source is working」が表示されることを確認
6. 左メニュー → **Dashboards** → 「DMARC Report Overview」を開く
7. 各パネルのデータが表示されない場合は、パネルをEditで開き「Run query」を実行後に保存
   - **補足**: Daily DMARC Resultsで「Run Query」を押した際、「Refresh」ボタンがリフレッシュ中（「Cancel」表記）にならない場合は、クエリセクションを一旦閉じるなどして「Run Query」ボタンを表示し直してから再度押してください

## ダッシュボード

デプロイ後、Grafanaダッシュボードには以下のパネルが含まれます:

- **Daily DMARC Results**: 日別のpass/fail推移
- **Source IP x Organization x Domain (Top 300 Fail Count)**: 送信元IP×組織×ドメイン×header_from別のfail数上位300件
- **SPF Results**: SPF認証結果の内訳
- **DKIM Results**: DKIM認証結果の内訳

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
