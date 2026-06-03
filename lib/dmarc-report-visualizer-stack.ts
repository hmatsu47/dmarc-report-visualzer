import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { StorageConstruct } from "./constructs/storage";
import { IngestionConstruct } from "./constructs/ingestion";
import { ParserConstruct } from "./constructs/parser";
import { CatalogConstruct } from "./constructs/catalog";
import { VisualizationConstruct } from "./constructs/visualization";
import { getOrCreateUlid } from "./utils/ulid";

export interface DmarcReportVisualizerStackProps extends cdk.StackProps {
  receiveDomain: string;
  glacierTransitionDays?: number;
  expirationDays?: number;
}

export class DmarcReportVisualizerStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: DmarcReportVisualizerStackProps) {
    super(scope, id, props);

    const ulid = getOrCreateUlid();

    const storage = new StorageConstruct(this, "Storage", {
      ulid,
      glacierTransitionDays: props.glacierTransitionDays ?? 395,
      expirationDays: props.expirationDays ?? 760,
    });

    new IngestionConstruct(this, "Ingestion", {
      receiveDomain: props.receiveDomain,
      receiveBucket: storage.receiveBucket,
    });

    new ParserConstruct(this, "Parser", {
      receiveBucket: storage.receiveBucket,
      athenaBucket: storage.athenaBucket,
    });

    const catalog = new CatalogConstruct(this, "Catalog", {
      athenaBucket: storage.athenaBucket,
      athenaResultsBucket: storage.athenaResultsBucket,
    });

    new VisualizationConstruct(this, "Visualization", {
      athenaBucket: storage.athenaBucket,
      athenaResultsBucket: storage.athenaResultsBucket,
      glueDatabaseName: "dmarc_reports",
      athenaWorkgroupName: "dmarc-workgroup",
    });

    // 出力
    new cdk.CfnOutput(this, "ReceiveBucketName", {
      value: storage.receiveBucket.bucketName,
      description: "S3 bucket for incoming DMARC report emails",
    });
    new cdk.CfnOutput(this, "AthenaBucketName", {
      value: storage.athenaBucket.bucketName,
      description: "S3 bucket for Parquet data",
    });
  }
}
