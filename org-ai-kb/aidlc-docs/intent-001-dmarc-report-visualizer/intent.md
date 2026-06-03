# Intent

## Prompt

AI-DLCを使って、DMARCレポートの受信・可視化ツールを作りたい。SESで受信してS3にDMARCレポートメールを保管、Lambdaで添付ファイルのXMLを解析してManaged Grafanaで可視化。CDKでIaC化し、複数AWSアカウントへのデプロイに対応。

## Summary

SESでDMARCレポートメールを受信しS3に保管、Lambda関数で添付ファイル（XML/ZIP）をパースしParquet形式に変換してS3に出力、AthenaをデータソースとしてAmazon Managed Grafanaで可視化するシステムをAWS CDKで構築する。IAM Identity Centerによる認証でエンジニア5名が利用。参考コード（lambda-email-parser）をベースにZIP対応・Parquet出力に修正する。

## Slug

dmarc-report-visualizer

## Type

feature
