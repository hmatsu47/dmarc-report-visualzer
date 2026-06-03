import { Construct } from "constructs";
import * as ses from "aws-cdk-lib/aws-ses";
import * as sesActions from "aws-cdk-lib/aws-ses-actions";
import * as s3 from "aws-cdk-lib/aws-s3";

export interface IngestionConstructProps {
  receiveDomain: string;
  receiveBucket: s3.IBucket;
}

export class IngestionConstruct extends Construct {
  public readonly receiptRuleSet: ses.ReceiptRuleSet;

  constructor(scope: Construct, id: string, props: IngestionConstructProps) {
    super(scope, id);

    this.receiptRuleSet = new ses.ReceiptRuleSet(this, "RuleSet", {
      receiptRuleSetName: "DmarcReceiptRuleSet",
    });

    this.receiptRuleSet.addRule("DmarcRule", {
      recipients: [props.receiveDomain],
      scanEnabled: true,
      actions: [
        new sesActions.S3({
          bucket: props.receiveBucket,
          objectKeyPrefix: "incoming/",
        }),
      ],
    });
  }
}
