"""Grafana Dashboard Provisioner - Custom Resource Lambda"""
import json
import logging
import urllib.request
import urllib.error
import boto3
import cfnresponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

grafana = boto3.client("grafana")


def handler(event, context):
    try:
        props = event["ResourceProperties"]
        workspace_id = props["WorkspaceId"]
        dashboard_json = props["DashboardJson"]
        datasource_json = props["DatasourceJson"]
        request_type = event["RequestType"]

        if request_type == "Delete":
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            return

        # Grafana APIキーを作成（一時的）
        key_resp = grafana.create_workspace_service_account(
            name="cdk-provisioner",
            grafanaRole="ADMIN",
            workspaceId=workspace_id,
        )
        sa_id = key_resp["id"]

        token_resp = grafana.create_workspace_service_account_token(
            name="cdk-provisioner-token",
            serviceAccountId=str(sa_id),
            workspaceId=workspace_id,
            secondsToLive=300,
        )
        api_key = token_resp["serviceAccountToken"]["key"]

        # Workspace URLを取得
        ws = grafana.describe_workspace(workspaceId=workspace_id)
        endpoint = f"https://{ws['workspace']['endpoint']}"

        # データソース作成
        ds_config = json.loads(datasource_json)
        _grafana_api(endpoint, api_key, "POST", "/api/datasources", ds_config)

        # ダッシュボード作成
        db_config = json.loads(dashboard_json)
        payload = {"dashboard": db_config, "overwrite": True}
        _grafana_api(endpoint, api_key, "POST", "/api/dashboards/db", payload)

        # サービスアカウントをクリーンアップ
        grafana.delete_workspace_service_account(
            serviceAccountId=str(sa_id),
            workspaceId=workspace_id,
        )

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {"WorkspaceUrl": endpoint})

    except Exception as e:
        logger.error(f"Provisioning failed: {e}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)})


def _grafana_api(endpoint, api_key, method, path, body=None):
    """Grafana HTTP APIを呼び出す"""
    url = f"{endpoint}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        logger.error(f"Grafana API error: {e.code} {body}")
        if e.code == 409:  # Conflict (already exists)
            return None
        raise
