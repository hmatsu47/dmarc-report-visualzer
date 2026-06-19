# Units of Work

## Unit: dmarc-report-visualizer

- **Scope**: 全コンポーネント（EmailReceiver, DmarcReportParser, DataCatalog, Visualization, StorageManager）を含む単一CDKアプリケーション
- **Rationale**: 小規模プロジェクト（5コンポーネント、単一チーム5名）であり、コンポーネント間の結合度が高い（SES→S3→Lambda→S3→Athena→Grafanaの一連パイプライン）。分割してもデプロイ独立性のメリットが薄く、統合テストの複雑化のみ招くため単一ユニットとする。
- **Technology**: AWS CDK（TypeScript）+ Lambda関数（Python）
- **Repository**: 本リポジトリ（dmarc-report-visualzer）
- **Stories covered**: S-1〜S-15（全ストーリー）
- **Components included**:
  - EmailReceiver
  - DmarcReportParser
  - DataCatalog
  - Visualization
  - StorageManager
