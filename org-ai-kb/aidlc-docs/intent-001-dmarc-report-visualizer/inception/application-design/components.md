# Components

## EmailReceiver

- **Purpose**: SES経由でDMARCレポートメールを受信しS3に保管する
- **Responsibilities**:
  - SES Receipt Ruleの定義（受信ドメイン → S3アクション）
  - 受信メールのRFC822形式でのS3保管
- **State**: ステートレス（SESマネージドサービス）
- **Owns**: なし（メールオブジェクトはS3に委譲）

## DmarcReportParser

- **Purpose**: S3に保管されたDMARCレポートメールを解析し、Parquet形式に変換して出力する
- **Responsibilities**:
  - メールMIME構造の解析と添付ファイル抽出
  - gzip/ZIP展開
  - DMARCレポートXMLのパースとフィールドフラット化
  - Parquetファイル生成とAthena用S3バケットへの出力
  - XXE攻撃の防止
  - エラー時のDLQ送信
- **State**: ステートレス（Lambda関数）
- **Owns**: DmarcReport（パース後の論理エンティティ）

## DataCatalog

- **Purpose**: Athenaでクエリ可能なテーブル定義を管理する
- **Responsibilities**:
  - Glue Databaseの定義
  - DMARCレポートテーブルのスキーマ定義
  - パーティション構成の管理
- **State**: ステートフル（Glue Data Catalogメタデータ）
- **Owns**: テーブルスキーマ定義

## Visualization

- **Purpose**: DMARCレポートデータをGrafanaダッシュボードで可視化する
- **Responsibilities**:
  - Managed Grafana Workspaceの提供
  - Athenaデータソース接続
  - ダッシュボードパネルの表示（認証推移、IP別結果、ドメイン統計、SPF/DKIM内訳）
  - IAM Identity Center認証
- **State**: ステートフル（ダッシュボード設定、データソース設定）
- **Owns**: ダッシュボード定義

## StorageManager

- **Purpose**: S3バケットのライフサイクル管理とアクセス制御を統括する
- **Responsibilities**:
  - 受信メール用バケットの管理
  - Parquet出力用バケットの管理
  - ライフサイクルポリシー（Glacier移行・削除）の適用
  - 暗号化とパブリックアクセスブロック
  - バケット名のULIDサフィックス付与
- **State**: ステートフル（S3オブジェクト）
- **Owns**: S3バケット設定、ライフサイクルルール
