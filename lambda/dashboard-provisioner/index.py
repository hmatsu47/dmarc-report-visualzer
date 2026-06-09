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

        # Athenaプラグインをインストール（既にあれば409で無視）
        _grafana_api(endpoint, api_key, "POST", "/api/plugins/grafana-athena-datasource/install")

        # データソース作成または更新
        ds_config = json.loads(datasource_json)
        ds_uid = None

        # 既存データソースを一覧から名前で検索
        all_ds = _grafana_api(endpoint, api_key, "GET", "/api/datasources") or []
        existing = next((ds for ds in all_ds if ds.get("name") == ds_config["name"]), None)
        logger.info(json.dumps({"event": "datasource.search", "found": existing is not None, "total": len(all_ds)}))

        if existing:
            # 既存を更新（UIDは変えない）
            ds_config["id"] = existing["id"]
            ds_config["uid"] = existing["uid"]
            _grafana_api(endpoint, api_key, "PUT", f"/api/datasources/{existing['id']}", ds_config)
            ds_uid = existing["uid"]
            logger.info(json.dumps({"event": "datasource.updated", "uid": ds_uid}))
        else:
            # 新規作成
            resp = _grafana_api(endpoint, api_key, "POST", "/api/datasources", ds_config)
            ds_uid = resp["datasource"]["uid"] if resp and "datasource" in resp else ds_config.get("uid")
            logger.info(json.dumps({"event": "datasource.created", "uid": ds_uid}))

        # ダッシュボード作成（データソースUIDを実際の値で置換）
        db_config = json.loads(dashboard_json.replace("dmarc-athena-ds", ds_uid))
        db_config["id"] = None
        payload = {"dashboard": db_config, "overwrite": True}
        db_resp = _grafana_api(endpoint, api_key, "POST", "/api/dashboards/db", payload)
        logger.info(json.dumps({"event": "dashboard.posted", "response": str(db_resp)[:500]}))

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
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        logger.warning(f"Grafana API {method} {path}: {e.code} {err_body}")
        if e.code in (409, 404):
            return None
        raise
