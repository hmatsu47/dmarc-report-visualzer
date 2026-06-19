# Domain Entities

## DmarcReportEmail

メールとして受信されたDMARCレポートの生データ。

| Field | Type | Description |
|-------|------|-------------|
| s3_bucket | string | 保管先バケット名 |
| s3_key | string | オブジェクトキー |
| received_at | timestamp | 受信日時（S3イベント時刻） |

## DmarcAttachment

メールから抽出されたDMARCレポート添付ファイル。

| Field | Type | Description |
|-------|------|-------------|
| filename | string | 添付ファイル名 |
| content_type | string | MIMEタイプ |
| content | bytes | 生バイナリデータ |
| compression | enum(gzip, zip, none) | 圧縮形式 |

## DmarcReportXml

展開・抽出後のDMARCレポートXMLドキュメント。

| Field | Type | Description |
|-------|------|-------------|
| xml_content | bytes | 展開後XMLバイト列 |
| source_filename | string | 元ファイル名（ZIP内パス含む） |

## DmarcRecord

フラット化後の1レコード（Parquet出力の1行に対応）。

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| report_id | string | No | レポート一意識別子 |
| org_name | string | No | レポート送信元組織名 |
| email | string | No | 送信元メールアドレス |
| extra_contact_info | string | Yes | 追加連絡先 |
| date_range_begin | timestamp | No | 対象期間開始（パーティションキー導出元） |
| date_range_end | timestamp | No | 対象期間終了 |
| domain | string | No | ポリシー適用ドメイン |
| adkim | string | No | DKIM alignment (r/s) |
| aspf | string | No | SPF alignment (r/s) |
| policy_p | string | No | ドメインポリシー |
| policy_sp | string | Yes | サブドメインポリシー |
| policy_pct | integer | No | ポリシー適用率 |
| source_ip | string | No | 送信元IP |
| reverse_dns | string | Yes | 送信元IPの逆引きDNS結果 |
| count | integer | No | メッセージ数 |
| disposition | string | No | 適用disposition |
| dkim_domain | string | Yes | DKIM認証ドメイン |
| dkim_result | string | Yes | DKIM認証結果 |
| dkim_selector | string | Yes | DKIMセレクタ |
| spf_domain | string | Yes | SPF認証ドメイン |
| spf_result | string | Yes | SPF認証結果 |
| policy_evaluated_dkim | string | No | DMARC評価DKIM (pass/fail) |
| policy_evaluated_spf | string | No | DMARC評価SPF (pass/fail) |
| header_from | string | Yes | Fromヘッダーのドメイン |

## Parquet Schema (PyArrow)

```python
schema = pa.schema([
    ("report_id", pa.string()),
    ("org_name", pa.string()),
    ("email", pa.string()),
    ("extra_contact_info", pa.string()),
    ("date_range_begin", pa.timestamp("s")),
    ("date_range_end", pa.timestamp("s")),
    ("domain", pa.string()),
    ("adkim", pa.string()),
    ("aspf", pa.string()),
    ("policy_p", pa.string()),
    ("policy_sp", pa.string()),
    ("policy_pct", pa.int32()),
    ("source_ip", pa.string()),
    ("reverse_dns", pa.string()),
    ("count", pa.int64()),
    ("disposition", pa.string()),
    ("dkim_domain", pa.string()),
    ("dkim_result", pa.string()),
    ("dkim_selector", pa.string()),
    ("spf_domain", pa.string()),
    ("spf_result", pa.string()),
    ("policy_evaluated_dkim", pa.string()),
    ("policy_evaluated_spf", pa.string()),
    ("header_from", pa.string()),
])
```
