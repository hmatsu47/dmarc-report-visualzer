# Requirements

## Intent Summary

- **Type**: 新機能（feature）
- **Scope**: システム全体（SES受信 → Lambda解析 → S3/Athena → Managed Grafana）
- **Complexity**: 中（複数AWSサービス連携、CDK IaC化）
- **Classification**: グリーンフィールド
- **Affected repos**: なし（新規作成）

## Functional Requirements

### メール受信・保管

- **FR-1**: SESでDMARCレポートメール（RFC5965/RFC7489準拠）を受信し、S3バケットにRFC822形式で保管する
- **FR-2**: 受信ドメインはCDKパラメータとして外部から指定できる
- **FR-3**: SESのドメイン検証（MXレコード設定等）はCDK管理外とし、手動で実施する前提とする

### メール解析・変換

- **FR-4**: S3にDMARCレポートメールが保管されたことをトリガーにLambda関数を起動する
- **FR-5**: Lambda関数はメールのMIME構造を解析し、DMARCレポートの添付ファイルを抽出する
- **FR-6**: 以下の圧縮・非圧縮形式に対応する
  - gzip（.gz）— Content-Type: application/gzip, application/x-gzip
  - ZIP（.zip）— Content-Type: application/zip, application/x-zip-compressed
  - 非圧縮XML（.xml）— Content-Type: text/xml, application/xml
- **FR-7**: 抽出したDMARCレポートXMLをパースし、以下のフィールドをフラット化してApache Parquet形式に変換する
  - レポートメタデータ: org_name, email, extra_contact_info, report_id, date_range_begin, date_range_end
  - ポリシー公開情報: domain, adkim, aspf, p, sp, pct
  - レコード: source_ip, count, disposition, dkim_domain, dkim_result, dkim_selector, spf_domain, spf_result, policy_evaluated_dkim, policy_evaluated_spf
- **FR-8**: 変換後のParquetファイルをAthenaクエリ用のS3バケットに出力する
- **FR-9**: 参考コード（lambda-email-parser/lambda_function_dmarc.py）をベースとし、JSON出力をParquet出力に変更、ZIP形式対応を追加する

### データカタログ・クエリ

- **FR-10**: AWS Glue Data CatalogにDMARCレポート用テーブル定義を自動作成する（CDK管理）
- **FR-11**: Amazon AthenaでParquetデータをクエリできるようにする
- **FR-12**: パーティション構成はdate_range_begin（日付）ベースとする

### 可視化

- **FR-13**: Amazon Managed Grafana Workspaceを作成し、Athenaをデータソースとして設定する
- **FR-14**: IAM Identity Centerを認証方式として使用する
- **FR-15**: ダッシュボード定義（JSON）をリポジトリで管理し、デプロイ時にプロビジョニングする
- **FR-16**: 初期ダッシュボードとして以下のパネルを含む
  - 日別DMARC認証結果サマリー（pass/fail推移）
  - 送信元IPごとの認証結果一覧
  - ドメイン別レポート統計
  - SPF/DKIM個別結果の内訳

### IaC・デプロイ

- **FR-17**: すべてのAWSリソースをAWS CDK（TypeScript）で定義する
- **FR-18**: S3バケット名はサフィックスとしてULIDを付与し一意性を確保する
- **FR-19**: ARNなど環境依存の識別子はCDKパラメータ（CfnParameter or context）で外部指定する
- **FR-20**: 複数のAWSアカウントにデプロイ可能な設計とする

## Non-Functional Requirements

### パフォーマンス

- **NFR-1**: Lambda関数は単一DMARCレポートメールを30秒以内に処理完了する
- **NFR-2**: Athenaクエリは1ヶ月分のデータに対して10秒以内に結果を返す

### セキュリティ

- **NFR-3**: S3バケットはパブリックアクセスを完全にブロックする
- **NFR-4**: S3バケットはSSE-S3またはSSE-KMSで暗号化する
- **NFR-5**: Lambda関数は最小権限のIAMロールで実行する
- **NFR-6**: XMLパーサーはXXE（XML External Entity）攻撃を防止する設定で使用する
- **NFR-7**: Managed GrafanaへのアクセスはIAM Identity Center認証を必須とする

### 可用性・運用

- **NFR-8**: Lambda関数のエラー時にDead Letter Queue（SQS）でリトライ可能とする
- **NFR-9**: Lambda関数の実行ログはCloudWatch Logsに出力する
- **NFR-10**: S3データのライフサイクルポリシーを設定する
  - Glacier移行: デフォルト13ヶ月（パラメータで変更可能）
  - 削除: デフォルト25ヶ月（パラメータで変更可能）

### 保守性

- **NFR-11**: CDKコードはTypeScriptで記述し、型安全性を確保する
- **NFR-12**: Lambda関数はPythonで実装する（参考コードとの一貫性）

## Assumptions

- DMARCレポートの送信元は1日あたり数十〜数百通程度の規模を想定
- IAM Identity Centerは対象AWSアカウントで既に有効化済み（Organizations環境前提）
- デプロイ先アカウントにはCDKのブートストラップが完了済み
- 受信ドメインのDNS管理権限はユーザーが保持している（手動でMXレコード設定可能）
- GrafanaダッシュボードのプロビジョニングにはGrafana HTTP APIを使用する

## Out of Scope

- SESドメイン検証のDNSレコード自動作成（手動前提）
- メール本文のテキスト解析（DMARCレポート添付ファイルのみ対象）
- DMARCレポート以外のメール処理
- マルチリージョンデプロイ
- CI/CDパイプラインの構築
- アラート通知（Grafanaアラート機能は今後の拡張として検討）
- WorkMail連携（参考コードにあるが本システムでは不要）
