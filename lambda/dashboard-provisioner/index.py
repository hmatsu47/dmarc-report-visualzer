"""Grafana Dashboard Provisioner - Custom Resource Lambda (Provider framework)"""
import json
import logging
import urllib.request
import urllib.error
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

grafana_client = boto3.client("grafana")

# 固定のサービスアカウント名（毎回同じものを再利用する）
SA_NAME = "cdk-provisioner"


def on_event(event, context):
    """CDK Provider フレームワーク用ハンドラー"""
    request_type = event["RequestType"]
    props = event["ResourceProperties"]

    if request_type == "Delete":
        # 削除時にサービスアカウントもクリーンアップ
        workspace_id = props["WorkspaceId"]
        _delete_sa_if_exists(workspace_id)
        return {"PhysicalResourceId": event.get("PhysicalResourceId", "none")}

    workspace_id = props["WorkspaceId"]
    dashboard_json = props["DashboardJson"]
    datasource_json = props["DatasourceJson"]

    # 既存のサービスアカウントを検索し、なければ作成
    sa_id = _find_or_create_sa(workspace_id)

    # 既存トークンは使い回せないため新規発行（短命）
    token_resp = grafana_client.create_workspace_service_account_token(
        name="deploy-token",
        serviceAccountId=str(sa_id),
        workspaceId=workspace_id,
        secondsToLive=300,
    )
    api_key = token_resp["serviceAccountToken"]["key"]

    ws = grafana_client.describe_workspace(workspaceId=workspace_id)
    endpoint = f"https://{ws['workspace']['endpoint']}"

    # Athenaプラグインをインストール（既にあれば409で無視）
    _grafana_api(endpoint, api_key, "POST", "/api/plugins/grafana-athena-datasource/install")

    # データソース作成または更新
    ds_config = json.loads(datasource_json)
    all_ds = _grafana_api(endpoint, api_key, "GET", "/api/datasources") or []
    existing = next((ds for ds in all_ds if ds.get("name") == ds_config["name"]), None)
    logger.info(json.dumps({"event": "datasource.search", "found": existing is not None, "total": len(all_ds)}))

    if existing:
        ds_config["id"] = existing["id"]
        ds_config["uid"] = existing["uid"]
        _grafana_api(endpoint, api_key, "PUT", f"/api/datasources/{existing['id']}", ds_config)
        ds_uid = existing["uid"]
        logger.info(json.dumps({"event": "datasource.updated", "uid": ds_uid}))
    else:
        resp = _grafana_api(endpoint, api_key, "POST", "/api/datasources", ds_config)
        ds_uid = resp["datasource"]["uid"] if resp and "datasource" in resp else ds_config.get("uid")
        logger.info(json.dumps({"event": "datasource.created", "uid": ds_uid}))

    # ダッシュボード作成
    db_config = json.loads(dashboard_json.replace("dmarc-athena-ds", ds_uid))
    db_config["id"] = None
    payload = {"dashboard": db_config, "overwrite": True}
    db_resp = _grafana_api(endpoint, api_key, "POST", "/api/dashboards/db", payload)
    logger.info(json.dumps({"event": "dashboard.posted", "response": str(db_resp)[:500]}))

    return {
        "PhysicalResourceId": f"grafana-dashboard-{workspace_id}",
        "Data": {"WorkspaceUrl": endpoint},
    }


def _find_or_create_sa(workspace_id):
    """既存のサービスアカウントを名前で検索し、なければ作成する。古い日付入りSAは削除する。"""
    found_id = None
    stale_sas = []
    paginator_token = None
    while True:
        params = {"workspaceId": workspace_id}
        if paginator_token:
            params["nextToken"] = paginator_token
        resp = grafana_client.list_workspace_service_accounts(**params)
        for sa in resp.get("serviceAccounts", []):
            if sa["name"] == SA_NAME:
                found_id = sa["id"]
            elif sa["name"].startswith(SA_NAME):
                stale_sas.append(sa)
        paginator_token = resp.get("nextToken")
        if not paginator_token:
            break

    # 古い日付入りサービスアカウントを削除
    for sa in stale_sas:
        try:
            grafana_client.delete_workspace_service_account(
                serviceAccountId=str(sa["id"]), workspaceId=workspace_id
            )
            logger.info(json.dumps({"event": "sa.stale_deleted", "id": sa["id"], "name": sa["name"]}))
        except Exception as e:
            logger.warning(f"Failed to delete stale SA {sa['name']}: {e}")

    if found_id:
        logger.info(json.dumps({"event": "sa.reused", "id": found_id}))
        return found_id

    # 見つからなかったので新規作成
    create_resp = grafana_client.create_workspace_service_account(
        name=SA_NAME,
        grafanaRole="ADMIN",
        workspaceId=workspace_id,
    )
    logger.info(json.dumps({"event": "sa.created", "id": create_resp["id"]}))
    return create_resp["id"]


def _delete_sa_if_exists(workspace_id):
    """サービスアカウントが存在すれば削除する"""
    try:
        resp = grafana_client.list_workspace_service_accounts(workspaceId=workspace_id)
        for sa in resp.get("serviceAccounts", []):
            if sa["name"] == SA_NAME:
                grafana_client.delete_workspace_service_account(
                    serviceAccountId=str(sa["id"]),
                    workspaceId=workspace_id,
                )
                logger.info(json.dumps({"event": "sa.deleted", "id": sa["id"]}))
    except Exception as e:
        logger.warning(f"Failed to delete SA: {e}")


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
