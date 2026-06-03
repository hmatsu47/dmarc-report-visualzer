# Workflow Rationale

## Inception phase

- **requirements-analysis**: 含む — SES受信/Lambda解析/Athena/Grafana連携の要件を整理する必要がある
- **user-stories**: 含む — 管理者（設定・デプロイ）と閲覧者（ダッシュボード参照）の複数シナリオがある
- **application-design**: 含む — SES/S3/Lambda/Athena/Grafana の複数コンポーネント連携の設計が必要
- **units-generation**: 含む — 単一ユニット確認のため形式的に実行（ユーザー合意済み）
- **reverse-engineering**: スキップ — グリーンフィールド、既存コードへの変更なし
- **wireframes**: スキップ — UIはManaged Grafanaのダッシュボードで構築するためカスタムUI設計は不要

## Construction phase (単一ユニット: dmarc-report-visualizer)

- **functional-design**: 含む — XMLパース、ZIP展開、Parquet変換のドメインロジック設計
- **nfr-assessment**: 含む — マルチアカウントデプロイ、パラメータ化、セキュリティ要件の評価
- **nfr-design**: 含む — CDKパラメータ設計、暗号化、アクセス制御パターン
- **infrastructure-design**: 含む — CDKスタック構成、SES/S3/Lambda/Athena/Grafanaのリソース定義
- **code-generation**: 含む — CDKコードおよびLambda関数の実装
- **build-and-test**: スキップ — 未実装（🚧）

## Lenses

- **owasp**: 有効 — DMARCレポートには送信元IP等の情報を含むため、XMLパース時のXXE対策やS3アクセス制御などセキュリティ観点が重要
