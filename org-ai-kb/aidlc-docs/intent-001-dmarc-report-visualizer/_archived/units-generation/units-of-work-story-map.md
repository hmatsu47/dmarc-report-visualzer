# Units of Work — Story Map

## dmarc-report-visualizer

| Story | Component(s) | Category |
|-------|-------------|----------|
| S-1 | EmailReceiver, StorageManager | メール受信・保管 |
| S-2 | DmarcReportParser, StorageManager | メール解析（gzip） |
| S-3 | DmarcReportParser, StorageManager | メール解析（ZIP） |
| S-4 | DmarcReportParser, StorageManager | メール解析（非圧縮XML） |
| S-5 | DmarcReportParser | エラーリトライ |
| S-6 | DataCatalog | データカタログ |
| S-7 | Visualization, DataCatalog | 可視化（日別推移） |
| S-8 | Visualization, DataCatalog | 可視化（IP別） |
| S-9 | Visualization, DataCatalog | 可視化（ドメイン別） |
| S-10 | Visualization, DataCatalog | 可視化（SPF/DKIM） |
| S-11 | 全コンポーネント | IaCデプロイ |
| S-12 | StorageManager | ライフサイクル |
| S-13 | DmarcReportParser | セキュリティ（XXE） |
| S-14 | StorageManager | セキュリティ（S3） |
| S-15 | Visualization | ダッシュボード管理 |
