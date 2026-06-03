import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cdk from "aws-cdk-lib";

export interface StorageConstructProps {
  ulid: string;
  glacierTransitionDays: number;
  expirationDays: number;
}

export class StorageConstruct extends Construct {
  public readonly receiveBucket: s3.Bucket;
  public readonly athenaBucket: s3.Bucket;
  public readonly athenaResultsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StorageConstructProps) {
    super(scope, id);

    this.receiveBucket = new s3.Bucket(this, "ReceiveBucket", {
      bucketName: `dmarc-receive-${props.ulid}`,
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.athenaBucket = new s3.Bucket(this, "AthenaBucket", {
      bucketName: `dmarc-athena-${props.ulid}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          prefix: "dmarc-reports/",
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(props.glacierTransitionDays),
            },
          ],
          expiration: cdk.Duration.days(props.expirationDays),
        },
      ],
    });

    this.athenaResultsBucket = new s3.Bucket(this, "AthenaResultsBucket", {
      bucketName: `dmarc-athena-results-${props.ulid}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(7),
        },
      ],
    });
  }
}
