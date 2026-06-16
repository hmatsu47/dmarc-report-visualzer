import { Construct } from "constructs";
import * as grafana from "aws-cdk-lib/aws-grafana";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as cr from "aws-cdk-lib/custom-resources";
import * as cdk from "aws-cdk-lib";
import * as path from "path";
import * as fs from "fs";

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
          "athena:ListWorkGroups",
          "athena:ListDataCatalogs",
          "athena:ListDatabases",
          "athena:ListTableMetadata",
        ],
        resources: ["*"],
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
      pluginAdminEnabled: true,
      grafanaVersion: "12.4",
    });

    // ダッシュボードプロビジョナー
    const provisionerFn = new lambda.Function(this, "ProvisionerFunction", {
      runtime: lambda.Runtime.PYTHON_3_13,
      architecture: lambda.Architecture.ARM_64,
      handler: "index.on_event",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../lambda/dashboard-provisioner")),
      timeout: cdk.Duration.minutes(5),
    });

    provisionerFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "grafana:DescribeWorkspace",
          "grafana:ListWorkspaceServiceAccounts",
          "grafana:CreateWorkspaceServiceAccount",
          "grafana:CreateWorkspaceServiceAccountToken",
          "grafana:DeleteWorkspaceServiceAccount",
          "grafana:ListWorkspaceServiceAccountTokens",
          "grafana:DeleteWorkspaceServiceAccountToken",
        ],
        resources: ["*"],
      })
    );

    const datasourceJson = fs.readFileSync(
      path.join(__dirname, "../../grafana/datasources/athena.json"), "utf-8"
    ).replaceAll("${AWS_REGION}", cdk.Stack.of(this).region)
     .replace("${RESULTS_BUCKET}", props.athenaResultsBucket.bucketName);

    const dashboardJson = fs.readFileSync(
      path.join(__dirname, "../../grafana/dashboards/dmarc-overview.json"), "utf-8"
    );

    const provider = new cr.Provider(this, "ProvisionerProvider", {
      onEventHandler: provisionerFn,
    });

    new cdk.CustomResource(this, "DashboardProvisionerV2", {
      serviceToken: provider.serviceToken,
      properties: {
        WorkspaceId: this.workspace.ref,
        DatasourceJson: datasourceJson,
        DashboardJson: dashboardJson,
        Version: "19",
      },
    });
  }
}
