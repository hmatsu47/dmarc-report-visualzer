import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as logs from "aws-cdk-lib/aws-logs";
import * as cdk from "aws-cdk-lib";
import * as path from "path";

export interface ParserConstructProps {
  receiveBucket: s3.IBucket;
  athenaBucket: s3.IBucket;
}

export class ParserConstruct extends Construct {
  public readonly parserFunction: lambda.Function;
  public readonly deadLetterQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props: ParserConstructProps) {
    super(scope, id);

    this.deadLetterQueue = new sqs.Queue(this, "DLQ", {
      queueName: "DmarcParserDLQ",
      retentionPeriod: cdk.Duration.days(14),
    });

    // Layer: デプロイ前に `cd layer && pip install -r requirements.txt -t python` を実行しておくこと
    const parserLayer = new lambda.LayerVersion(this, "ParserLayer", {
      code: lambda.Code.fromAsset(path.join(__dirname, "../../layer")),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_14],
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      description: "pyarrow and defusedxml for DMARC parser",
    });

    this.parserFunction = new lambda.Function(this, "ParserFunction", {
      functionName: "dmarc-report-parser",
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "lambda_function.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../lambda/parser")),
      memorySize: 512,
      timeout: cdk.Duration.seconds(60),
      layers: [parserLayer],
      logRetention: logs.RetentionDays.ONE_MONTH,
      deadLetterQueue: this.deadLetterQueue,
      retryAttempts: 2,
      environment: {
        ATHENA_BUCKET: props.athenaBucket.bucketName,
        OUTPUT_PREFIX: "dmarc-reports",
      },
    });

    // S3読み取り権限（受信バケット）
    props.receiveBucket.grantRead(this.parserFunction);
    // S3書き込み権限（Athenaバケット、dmarc-reports/プレフィックスのみ）
    props.athenaBucket.grantPut(this.parserFunction, "dmarc-reports/*");

    // S3イベント通知
    props.receiveBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.parserFunction),
      { prefix: "incoming/" }
    );
  }
}
