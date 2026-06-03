# OWASP Lens Answers

## Data sensitivity

Internal — DMARCレポートには送信元IP、ドメイン名、認証結果が含まれるが、PII や機密データは含まない。組織内部のメールインフラ情報として Internal 分類。

## Compliance requirements

なし — 特定のコンプライアンスフレームワーク（GDPR、PCI-DSS等）の適用なし。AWSベストプラクティスに準拠する。

## Authentication model

IAM Identity Center（SAML/SSO）— Managed Grafana への認証はIAM Identity Center経由。Lambda/Athena はIAMロールベース。

## Internet-facing or internal

ミックス — SES受信エンドポイントはインターネットフェイシング（外部メールサーバーからDMARCレポートを受信）。Managed Grafanaダッシュボードは組織内部向け（Identity Center認証必須）。

## Known threat actors or attack vectors

- 悪意あるDMARCレポートの送信（不正なXML/ZIPによるLambda攻撃）
- S3バケットへの不正アクセス
- XMLパーサーを利用したXXE（XML External Entity）攻撃

## Risk tolerance

バランス型 — 内部ツールとして適切なセキュリティを維持しつつ、過度な制約は避ける。データ漏洩リスクは低（機密データなし）だが、インフラ侵害は防ぐ。
