import { Construct } from "constructs";
import * as grafana from "aws-cdk-lib/aws-grafana";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cdk from "aws-cdk-lib";

export interface VisualizationConstructProps {
  athenaBucket: s3.IBucket;
  athenaResultsBucket: s3.IBucket;
  glueDatabaseName: string;
  athenaWorkgroupName: string;
}

export class VisualizationConstruct extends Construct {
  public readonly workspace: grafana.CfnWorkspace;
  public readonly grafanaRole: iam.Role;

  constructor(scope: Construct, id: string, props: VisualizationConstructProps) {
    super(scope, id);

    this.grafanaRole = new iam.Role(this, "GrafanaRole", {
      assumedBy: new iam.ServicePrincipal("grafana.amazonaws.com"),
      description: "Role for Managed Grafana to access Athena and S3",
    });

    // Athena権限
    this.grafanaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup",
        ],
        resources: [
          cdk.Arn.format(
            { service: "athena", resource: "workgroup", resourceName: props.athenaWorkgroupName },
            cdk.Stack.of(this)
          ),
        ],
      })
    );

    // Glue権限
    this.grafanaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["glue:GetTable", "glue:GetPartitions", "glue:GetDatabase"],
        resources: [
          cdk.Arn.format({ service: "glue", resource: "catalog" }, cdk.Stack.of(this)),
          cdk.Arn.format(
            { service: "glue", resource: "database", resourceName: props.glueDatabaseName },
            cdk.Stack.of(this)
          ),
          cdk.Arn.format(
            { service: "glue", resource: "table", resourceName: `${props.glueDatabaseName}/*` },
            cdk.Stack.of(this)
          ),
        ],
      })
    );

    // S3権限（Athenaデータ読み取り）
    props.athenaBucket.grantRead(this.grafanaRole);
    // S3権限（Athena結果書き込み）
    props.athenaResultsBucket.grantReadWrite(this.grafanaRole);

    this.workspace = new grafana.CfnWorkspace(this, "Workspace", {
      name: "dmarc-dashboard",
      accountAccessType: "CURRENT_ACCOUNT",
      authenticationProviders: ["AWS_SSO"],
      permissionType: "SERVICE_MANAGED",
      dataSources: ["ATHENA"],
      roleArn: this.grafanaRole.roleArn,
    });
  }
}
