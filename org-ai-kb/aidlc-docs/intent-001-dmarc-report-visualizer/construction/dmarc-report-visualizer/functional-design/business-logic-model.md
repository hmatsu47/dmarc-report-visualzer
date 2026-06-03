# Business Logic Model

## 処理パイプライン概要

```
S3 Event (RFC822 email)
    │
    ▼
[1. メール取得]
    │
    ▼
[2. MIME解析・添付ファイル抽出]
    │
    ▼
[3. Content-Type判定・展開]
    ├── application/gzip, application/x-gzip → gzip展開
    ├── application/zip, application/x-zip-compressed → ZIP展開
    └── text/xml, application/xml → そのまま
    │
    ▼
[4. XMLパース（XXE無効化）]
    │
    ▼
[5. フラット化（メタデータ × ポリシー × レコード → 行）]
    │
    ▼
[6. Parquet生成・S3出力（日付パーティション）]
```

## ステップ詳細

### 1. メール取得

- S3イベントからバケット名・キーを取得
- S3からRFC822形式のメールオブジェクトを取得
- Pythonの`email`ライブラリで`message_from_bytes`パース

### 2. MIME解析・添付ファイル抽出

- `msg.walk()`で全MIMEパートを走査
- DMARCレポートに該当するパートを抽出する条件:
  - Content-Typeが`application/gzip`, `application/x-gzip`, `application/zip`, `application/x-zip-compressed`, `text/xml`, `application/xml`のいずれか
  - または、filenameが`.xml`, `.xml.gz`, `.gz`, `.zip`で終わるもの
- `multipart/*`パートはスキップ（コンテナのため）
- 該当しないパートは`dmarc.attachment.skipped`ログを出力しスキップ

### 3. Content-Type判定・展開

| Content-Type | 処理 |
|---|---|
| application/gzip, application/x-gzip | `gzip.decompress()` |
| application/zip, application/x-zip-compressed | `zipfile.ZipFile`で全エントリを展開。`.xml`拡張子のエントリのみ処理 |
| text/xml, application/xml | 展開不要。バイト列をそのまま使用 |

- ZIP内に複数XMLがある場合: 各XMLを独立して後続処理に渡す
- 展開失敗時: `PARSER_DECOMPRESS_FAILED`エラーをログ出力、当該添付をスキップして次へ（他の添付があれば処理続行）

### 4. XMLパース

- `defusedxml.ElementTree`を使用（外部エンティティ無効化）
- ルート要素が`<feedback>`であることを検証
- 必須要素の存在確認: `report_metadata`, `policy_published`, `record`（1つ以上）
- パース失敗時: `PARSER_INVALID_XML`エラー、当該XMLをスキップ

### 5. フラット化

1レポートXMLに対し、N行のレコードを生成する:

```
for each <record> in XML:
    row = {
        # report_metadata（全レコード共通）
        report_id, org_name, email, extra_contact_info,
        date_range_begin, date_range_end,
        # policy_published（全レコード共通）
        domain, adkim, aspf, policy_p, policy_sp, policy_pct,
        # record固有
        source_ip, count, disposition,
        policy_evaluated_dkim, policy_evaluated_spf,
        # auth_results（DKIM: 最初の結果を採用）
        dkim_domain, dkim_result, dkim_selector,
        # auth_results（SPF: 最初の結果を採用）
        spf_domain, spf_result
    }
```

- `date_range_begin`/`date_range_end`: UNIXタイムスタンプ（秒）→ ISO8601文字列に変換
- `auth_results/dkim`が複数ある場合: 最初のエントリを採用（他はログに記録）
- `auth_results/spf`が複数ある場合: 最初のエントリを採用
- オプショナルフィールドが欠落している場合: `None`（Parquetではnull）

### 6. Parquet生成・S3出力

- PyArrowを使用してParquet形式で書き込み（snappy圧縮）
- 出力パス: `s3://<athena-bucket>/dmarc-reports/year=YYYY/month=MM/day=DD/{report_id}.parquet`
  - YYYY/MM/DD は `date_range_begin` から導出
- 1つのXMLファイルにつき1つのParquetファイルを生成
- 空レコード（recordが0件）の場合はファイルを出力しない

## エラーハンドリング戦略

| 失敗箇所 | 挙動 |
|----------|------|
| S3からのメール取得失敗 | 例外をraiseしLambdaリトライ → 最終的にDLQ |
| MIME解析失敗（メールでない） | エラーログ出力、DLQへ |
| 個別添付の展開失敗 | 当該添付をスキップ、他の添付は処理続行 |
| XMLパース失敗 | 当該XMLをスキップ、他の添付は処理続行 |
| Parquet書き込み失敗 | 例外をraiseしLambdaリトライ → DLQ |
| 全添付がDMARCレポートでない | 正常終了（処理対象なし）、INFOログ出力 |

## 冪等性

- 同一メールが再処理された場合、同一パスに同一内容のParquetを上書きする（S3 PutObjectは冪等）
- report_idをファイル名に含めることで、異なるレポートが衝突しない
