import { Construct } from "constructs";
import * as glue from "aws-cdk-lib/aws-glue";
import * as athena from "aws-cdk-lib/aws-athena";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cdk from "aws-cdk-lib";

export interface CatalogConstructProps {
  athenaBucket: s3.IBucket;
  athenaResultsBucket: s3.IBucket;
}

export class CatalogConstruct extends Construct {
  public readonly database: glue.CfnDatabase;
  public readonly table: glue.CfnTable;
  public readonly workgroup: athena.CfnWorkGroup;

  constructor(scope: Construct, id: string, props: CatalogConstructProps) {
    super(scope, id);

    this.database = new glue.CfnDatabase(this, "Database", {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseInput: {
        name: "dmarc_reports",
        description: "DMARC aggregate report data catalog",
      },
    });

    const columns = [
      { name: "report_id", type: "string" },
      { name: "org_name", type: "string" },
      { name: "email", type: "string" },
      { name: "extra_contact_info", type: "string" },
      { name: "date_range_begin", type: "timestamp" },
      { name: "date_range_end", type: "timestamp" },
      { name: "domain", type: "string" },
      { name: "adkim", type: "string" },
      { name: "aspf", type: "string" },
      { name: "policy_p", type: "string" },
      { name: "policy_sp", type: "string" },
      { name: "policy_pct", type: "int" },
      { name: "source_ip", type: "string" },
      { name: "count", type: "bigint" },
      { name: "disposition", type: "string" },
      { name: "dkim_domain", type: "string" },
      { name: "dkim_result", type: "string" },
      { name: "dkim_selector", type: "string" },
      { name: "spf_domain", type: "string" },
      { name: "spf_result", type: "string" },
      { name: "policy_evaluated_dkim", type: "string" },
      { name: "policy_evaluated_spf", type: "string" },
      { name: "header_from", type: "string" },
    ];

    this.table = new glue.CfnTable(this, "Table", {
      catalogId: cdk.Aws.ACCOUNT_ID,
      databaseName: "dmarc_reports",
      tableInput: {
        name: "dmarc_aggregate_reports",
        description: "DMARC aggregate report records",
        tableType: "EXTERNAL_TABLE",
        parameters: {
          "classification": "parquet",
          "parquet.compression": "SNAPPY",
          "projection.enabled": "true",
          "projection.year.type": "integer",
          "projection.year.range": "2024,2030",
          "projection.month.type": "integer",
          "projection.month.range": "1,12",
          "projection.month.digits": "2",
          "projection.day.type": "integer",
          "projection.day.range": "1,31",
          "projection.day.digits": "2",
          "storage.location.template": `s3://${props.athenaBucket.bucketName}/dmarc-reports/year=\${year}/month=\${month}/day=\${day}`,
        },
        storageDescriptor: {
          location: `s3://${props.athenaBucket.bucketName}/dmarc-reports/`,
          inputFormat: "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
          outputFormat: "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
          serdeInfo: {
            serializationLibrary: "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe",
          },
          columns,
        },
        partitionKeys: [
          { name: "year", type: "string" },
          { name: "month", type: "string" },
          { name: "day", type: "string" },
        ],
      },
    });
    this.table.addDependency(this.database);

    this.workgroup = new athena.CfnWorkGroup(this, "Workgroup", {
      name: "dmarc-workgroup",
      state: "ENABLED",
      workGroupConfiguration: {
        enforceWorkGroupConfiguration: true,
        publishCloudWatchMetricsEnabled: true,
        bytesScannedCutoffPerQuery: 1_073_741_824, // 1 GB
        resultConfiguration: {
          outputLocation: `s3://${props.athenaResultsBucket.bucketName}/`,
        },
      },
    });
  }
}
