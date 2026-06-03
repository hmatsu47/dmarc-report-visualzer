# Business Rules

## BR-1: DMARCレポート添付ファイルの識別

添付ファイルがDMARCレポートであると判定する条件（OR）:
1. Content-Typeが以下のいずれか: `application/gzip`, `application/x-gzip`, `application/zip`, `application/x-zip-compressed`, `text/xml`, `application/xml`
2. filenameの拡張子が以下のいずれか: `.xml`, `.xml.gz`, `.gz`, `.zip`

いずれにも該当しない添付はDMARCレポートではないものとしてスキップする。

## BR-2: 圧縮形式の判定

Content-Typeが不正確な場合に備え、以下の順で判定する:
1. Content-Typeで判定（優先）
2. Content-Typeが`application/octet-stream`または不明の場合、filenameの拡張子で判定
3. 拡張子も不明の場合、マジックバイトで判定:
   - `1f 8b` → gzip
   - `50 4b 03 04` → ZIP
   - `3c 3f 78 6d 6c` (`<?xml`) → 非圧縮XML

## BR-3: ZIP内ファイルの選択

ZIPアーカイブ内のファイルは以下のルールで選択する:
- `.xml`拡張子を持つファイルのみ処理対象
- ディレクトリエントリはスキップ
- `__MACOSX/`プレフィックスのエントリはスキップ（macOS固有メタデータ）
- ZIP内に該当ファイルがない場合はWARNログを出力しスキップ

## BR-4: XMLルート要素の検証

パース後のXMLが有効なDMARCレポートであることを検証する:
- ルート要素のタグが`feedback`であること
- `report_metadata`子要素が存在すること
- `policy_published`子要素が存在すること
- `record`子要素が1つ以上存在すること

いずれかが欠落する場合は`PARSER_SCHEMA_MISMATCH`エラーとし当該XMLをスキップ。

## BR-5: タイムスタンプ変換

- `date_range/begin`および`date_range/end`はUNIXエポック秒（整数文字列）で格納されている
- これをPython datetimeに変換し、Parquetにはtimestamp型で保存する
- パーティションパス（year/month/day）は`date_range_begin`のUTC日付から導出

## BR-6: auth_resultsの多値対応

DMARCレポートの`auth_results`には同一認証方式で複数結果が含まれることがある:
- `dkim`: 複数結果がある場合、最初のエントリを主レコードに採用
- `spf`: 複数結果がある場合、最初のエントリを主レコードに採用
- 2つ目以降の結果はログに記録するが、現時点ではParquetには含めない

## BR-7: Parquetファイルの命名と配置

- 出力パス: `dmarc-reports/year={YYYY}/month={MM}/day={DD}/{report_id}.parquet`
- `{YYYY}`, `{MM}`, `{DD}`は`date_range_begin`のUTC年月日
- `{report_id}`はXML内の`report_metadata/report_id`の値
- 同一report_idのファイルが既に存在する場合は上書き（冪等性保証）

## BR-8: エラー発生時の部分処理

1つのメールに複数の添付がある場合:
- 個別の添付ファイルの処理失敗は当該ファイルのみスキップ
- 他の添付ファイルの処理は続行する
- すべての添付処理が完了した時点でLambdaは正常終了
- メール取得自体の失敗、またはすべての添付で処理失敗した場合のみ例外をraiseしDLQへ

## BR-9: Lambda関数の冪等性

- 同一S3イベントが複数回配信された場合（at-least-once）、同一出力を生成する
- report_idベースのファイル名により同一内容の上書きとなる
- 副作用（S3 PutObject）は冪等な操作

## BR-10: S3バケット名のULID付与

- バケット名: `{prefix}-{ulid}`
- ULIDはCDKデプロイ時に1回生成し、スタックのライフタイム中は固定
- CDK RemovalPolicy.RETAIN により、スタック削除時もバケットは保持
