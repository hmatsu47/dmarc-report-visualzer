"""Grafana Dashboard Provisioner - Custom Resource Lambda (Provider framework)"""
import json
import logging
import time
import urllib.request
import urllib.error
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

grafana_client = boto3.client("grafana")


def on_event(event, context):
    """CDK Provider フレームワーク用ハンドラー"""
    request_type = event["RequestType"]
    props = event["ResourceProperties"]

    if request_type == "Delete":
        return {"PhysicalResourceId": event.get("PhysicalResourceId", "none")}

    workspace_id = props["WorkspaceId"]
    dashboard_json = props["DashboardJson"]
    datasource_json = props["DatasourceJson"]

    # 一時的なサービスアカウント作成
    sa_name = f"cdk-provisioner-{int(time.time())}"
    key_resp = grafana_client.create_workspace_service_account(
        name=sa_name,
        grafanaRole="ADMIN",
        workspaceId=workspace_id,
    )
    sa_id = key_resp["id"]

    try:
        token_resp = grafana_client.create_workspace_service_account_token(
            name="token",
            serviceAccountId=str(sa_id),
            workspaceId=workspace_id,
            secondsToLive=300,
        )
        api_key = token_resp["serviceAccountToken"]["key"]

        # Workspace URLを取得
        ws = grafana_client.describe_workspace(workspaceId=workspace_id)
        endpoint = f"https://{ws['workspace']['endpoint']}"

        # データソース作成
        ds_config = json.loads(datasource_json)
        _grafana_api(endpoint, api_key, "POST", "/api/datasources", ds_config)

        # ダッシュボード作成
        db_config = json.loads(dashboard_json)
        payload = {"dashboard": db_config, "overwrite": True}
        _grafana_api(endpoint, api_key, "POST", "/api/dashboards/db", payload)

    finally:
        # サービスアカウントクリーンアップ
        grafana_client.delete_workspace_service_account(
            serviceAccountId=str(sa_id),
            workspaceId=workspace_id,
        )

    return {
        "PhysicalResourceId": f"grafana-dashboard-{workspace_id}",
        "Data": {"WorkspaceUrl": endpoint},
    }


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
        err_body = e.read().decode()
        logger.warning(f"Grafana API {method} {path}: {e.code} {err_body}")
        if e.code == 409:
            return None
        raise
