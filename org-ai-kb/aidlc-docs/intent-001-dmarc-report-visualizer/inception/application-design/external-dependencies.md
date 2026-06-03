# External Dependencies

## External DMARC Report Senders

- **Name**: 外部メールサーバー（Google, Microsoft, Yahoo等）
- **Purpose**: DMARCレポートを集約送信する外部組織のメールサーバー
- **Contract**: RFC5322準拠のメール、DMARCレポートXML（RFC7489）を添付（gzip/ZIP/非圧縮）
- **Failure mode**: 送信遅延・未送信は受信側で検知不能。データ欠損として許容する
- **Consumers**: EmailReceiver

## IAM Identity Center

- **Name**: AWS IAM Identity Center
- **Purpose**: Managed Grafanaへのユーザー認証を提供する
- **Contract**: SAML 2.0 / OIDC準拠の認証フロー
- **Failure mode**: 認証サービス停止時はGrafanaにログイン不可。データ損失なし
- **Consumers**: Visualization
