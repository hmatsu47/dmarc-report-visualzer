#!/bin/bash
# 既存メールを再パースして新スキーマのParquetを再生成するスクリプト
#
# 使用方法:
#   ./scripts/reprocess.sh
#
# 前提:
#   - AWS CLIが設定済み
#   - CloudFormation出力からバケット名を自動取得
#   - Lambda関数 dmarc-report-parser がデプロイ済み（新スキーマ対応版）

set -euo pipefail

STACK_NAME="DmarcReportVisualizerStack"
FUNCTION_NAME="dmarc-report-parser"

echo "=== スタック出力からバケット名を取得中... ==="
RECEIVE_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ReceiveBucketName'].OutputValue" --output text)
ATHENA_BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='AthenaBucketName'].OutputValue" --output text)

if [ -z "$RECEIVE_BUCKET" ] || [ -z "$ATHENA_BUCKET" ]; then
  echo "エラー: バケット名を取得できませんでした" >&2
  exit 1
fi

echo "受信バケット: $RECEIVE_BUCKET"
echo "Athenaバケット: $ATHENA_BUCKET"

echo ""
echo "=== 既存Parquetデータを削除中... ==="
aws s3 rm "s3://${ATHENA_BUCKET}/dmarc-reports/" --recursive
echo "削除完了"

echo ""
echo "=== 受信バケットのメールを再処理中... ==="
KEYS=$(aws s3api list-objects-v2 --bucket "$RECEIVE_BUCKET" --prefix "incoming/" \
  --query "Contents[].Key" --output text)

if [ -z "$KEYS" ] || [ "$KEYS" = "None" ]; then
  echo "再処理対象のメールがありません"
  exit 0
fi

TOTAL=$(echo "$KEYS" | wc -w)
COUNT=0
ERRORS=0

for KEY in $KEYS; do
  COUNT=$((COUNT + 1))
  echo "[$COUNT/$TOTAL] $KEY"

  PAYLOAD=$(printf '{"Records":[{"s3":{"bucket":{"name":"%s"},"object":{"key":"%s"}}}]}' "$RECEIVE_BUCKET" "$KEY")

  if ! aws lambda invoke --function-name "$FUNCTION_NAME" \
    --payload "$PAYLOAD" --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>/dev/null | head -1 | grep -q '"statusCode": 200'; then
    echo "  警告: 処理失敗 ($KEY)"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""
echo "=== 完了 ==="
echo "処理: $COUNT 件, エラー: $ERRORS 件"
