# Data Models

## DmarcReport

- **Owning component**: DmarcReportParser
- **Fields**:
  | Field | Type | Description |
  |-------|------|-------------|
  | report_id | string | レポート一意識別子 |
  | org_name | string | レポート送信元組織名 |
  | email | string | レポート送信元メールアドレス |
  | extra_contact_info | string (nullable) | 追加連絡先情報 |
  | date_range_begin | timestamp | レポート対象期間開始 |
  | date_range_end | timestamp | レポート対象期間終了 |
  | domain | string | ポリシー適用ドメイン |
  | adkim | string | DKIM alignment mode (r/s) |
  | aspf | string | SPF alignment mode (r/s) |
  | policy_p | string | ドメインポリシー (none/quarantine/reject) |
  | policy_sp | string (nullable) | サブドメインポリシー |
  | policy_pct | integer | ポリシー適用率 (0-100) |
  | source_ip | string | 送信元IPアドレス |
  | reverse_dns | string (nullable) | 送信元IPの逆引きDNS結果 |
  | count | integer | 当該IPからのメッセージ数 |
  | disposition | string | 適用されたdisposition (none/quarantine/reject) |
  | dkim_domain | string (nullable) | DKIM認証ドメイン |
  | dkim_result | string (nullable) | DKIM認証結果 (pass/fail/none) |
  | dkim_selector | string (nullable) | DKIMセレクタ |
  | spf_domain | string (nullable) | SPF認証ドメイン |
  | spf_result | string (nullable) | SPF認証結果 (pass/fail/softfail/neutral/none) |
  | policy_evaluated_dkim | string | DMARC評価でのDKIM結果 (pass/fail) |
  | policy_evaluated_spf | string | DMARC評価でのSPF結果 (pass/fail) |
  | header_from | string (nullable) | Fromヘッダーのドメイン |
- **Relationships**: なし（単一フラットテーブル）
- **Constraints**:
  - report_id + source_ip + dkim_domain + spf_domain の組み合わせで論理的に一意
  - date_range_begin は必須（パーティションキー）
  - count は正の整数
- **Lifecycle**:
  - 作成: Lambda関数によるParquet書き込み時
  - 更新: なし（追記のみ、イミュータブル）
  - 削除: S3ライフサイクルポリシーによる自動削除（デフォルト25ヶ月）

## Partitioning Strategy

- **パーティションキー**: `year=YYYY/month=MM/day=DD`（date_range_beginから導出）
- **ファイル形式**: Apache Parquet（snappy圧縮）
- **ファイル命名**: `{safe_org}__{report_id}.parquet`（org_nameをサニタイズして先頭に付加）
