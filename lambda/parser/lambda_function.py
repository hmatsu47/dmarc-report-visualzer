"""DMARC Report Parser Lambda - S3メールからParquet変換"""
import os
import re
import email
import gzip
import zipfile
import io
import json
import logging
from datetime import datetime, timezone

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import defusedxml.ElementTree as ET

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

ATHENA_BUCKET = os.environ["ATHENA_BUCKET"]
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "dmarc-reports")

SCHEMA = pa.schema([
    ("report_id", pa.string()),
    ("org_name", pa.string()),
    ("email", pa.string()),
    ("extra_contact_info", pa.string()),
    ("date_range_begin", pa.timestamp("s")),
    ("date_range_end", pa.timestamp("s")),
    ("domain", pa.string()),
    ("adkim", pa.string()),
    ("aspf", pa.string()),
    ("policy_p", pa.string()),
    ("policy_sp", pa.string()),
    ("policy_pct", pa.int32()),
    ("source_ip", pa.string()),
    ("count", pa.int64()),
    ("disposition", pa.string()),
    ("dkim_domain", pa.string()),
    ("dkim_result", pa.string()),
    ("dkim_selector", pa.string()),
    ("spf_domain", pa.string()),
    ("spf_result", pa.string()),
    ("policy_evaluated_dkim", pa.string()),
    ("policy_evaluated_spf", pa.string()),
    ("header_from", pa.string()),
])

DMARC_CONTENT_TYPES = {
    "application/gzip", "application/x-gzip",
    "application/zip", "application/x-zip-compressed",
    "text/xml", "application/xml",
}

DMARC_EXTENSIONS = {".xml", ".xml.gz", ".gz", ".zip"}


def handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    logger.info(json.dumps({"event": "dmarc.email.received", "bucket": bucket, "key": key}))

    obj = s3.get_object(Bucket=bucket, Key=key)
    msg = email.message_from_bytes(obj["Body"].read())

    attachments = _extract_attachments(msg)
    if not attachments:
        logger.info(json.dumps({"event": "dmarc.attachment.skipped", "reason": "no DMARC attachments found"}))
        return {"statusCode": 200, "body": "No DMARC attachments"}

    processed = 0
    for att in attachments:
        try:
            xml_contents = _decompress(att)
            for xml_bytes in xml_contents:
                records = _parse_xml(xml_bytes)
                if records:
                    _write_parquet(records)
                    processed += 1
        except Exception as e:
            logger.error(json.dumps({"event": "dmarc.parse.error", "filename": att["filename"], "error": str(e)}))
            continue

    if processed == 0:
        raise RuntimeError(f"All attachments failed processing for {key}")

    return {"statusCode": 200, "body": f"Processed {processed} report(s)"}


def _extract_attachments(msg):
    """MIMEパートからDMARCレポート添付を抽出"""
    attachments = []
    for part in msg.walk():
        ct = part.get_content_type()
        filename = part.get_filename() or ""

        if ct in DMARC_CONTENT_TYPES or any(filename.lower().endswith(ext) for ext in DMARC_EXTENSIONS):
            content = part.get_payload(decode=True)
            if content:
                attachments.append({"content_type": ct, "filename": filename, "content": content})

    return attachments


def _decompress(attachment):
    """圧縮形式に応じて展開し、XMLバイト列のリストを返す"""
    content = attachment["content"]
    ct = attachment["content_type"]
    filename = attachment["filename"].lower()

    # マジックバイトで判定
    if content[:2] == b"\x1f\x8b" or ct in ("application/gzip", "application/x-gzip") or filename.endswith(".gz"):
        xml = gzip.decompress(content)
        logger.info(json.dumps({"event": "dmarc.decompress.success", "type": "gzip"}))
        return [xml]

    if content[:4] == b"PK\x03\x04" or ct in ("application/zip", "application/x-zip-compressed") or filename.endswith(".zip"):
        results = []
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if name.startswith("__MACOSX/") or not name.lower().endswith(".xml") or name.endswith("/"):
                    continue
                results.append(zf.read(name))
        if not results:
            logger.warning(json.dumps({"event": "dmarc.decompress.error", "reason": "no XML in ZIP"}))
        else:
            logger.info(json.dumps({"event": "dmarc.decompress.success", "type": "zip", "files": len(results)}))
        return results

    # 非圧縮XML
    return [content]


def _parse_xml(xml_bytes):
    """DMARCレポートXMLをパースしてフラットレコードのリストを返す"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error(json.dumps({"event": "dmarc.xml.xxe_blocked", "error": str(e)}))
        return []

    if root.tag != "feedback":
        logger.error(json.dumps({"event": "dmarc.parse.error", "error_code": "PARSER_SCHEMA_MISMATCH", "root_tag": root.tag}))
        return []

    meta = root.find("report_metadata")
    policy = root.find("policy_published")
    record_elems = root.findall("record")

    if meta is None or policy is None or not record_elems:
        logger.error(json.dumps({"event": "dmarc.parse.error", "error_code": "PARSER_SCHEMA_MISMATCH"}))
        return []

    # メタデータ共通フィールド
    report_id = _text(meta, "report_id")
    org_name = _text(meta, "org_name")
    email_addr = _text(meta, "email")
    extra_contact = _text(meta, "extra_contact_info")
    date_begin = _ts(meta.find("date_range"), "begin")
    date_end = _ts(meta.find("date_range"), "end")

    # ポリシー共通フィールド
    domain = _text(policy, "domain")
    adkim = _text(policy, "adkim") or "r"
    aspf = _text(policy, "aspf") or "r"
    policy_p = _text(policy, "p")
    policy_sp = _text(policy, "sp")
    policy_pct = int(_text(policy, "pct") or "100")

    records = []
    for rec in record_elems:
        row_elem = rec.find("row")
        if row_elem is None:
            continue

        source_ip = _text(row_elem, "source_ip")
        count = int(_text(row_elem, "count") or "0")

        pe = row_elem.find("policy_evaluated")
        disposition = _text(pe, "disposition") if pe is not None else None
        pe_dkim = _text(pe, "dkim") if pe is not None else None
        pe_spf = _text(pe, "spf") if pe is not None else None

        # identifiers
        identifiers = rec.find("identifiers")
        header_from = _text(identifiers, "header_from") if identifiers is not None else None

        # auth_results
        auth = rec.find("auth_results")
        dkim_domain = dkim_result = dkim_selector = None
        spf_domain = spf_result = None

        if auth is not None:
            dkim_elem = auth.find("dkim")
            if dkim_elem is not None:
                dkim_domain = _text(dkim_elem, "domain")
                dkim_result = _text(dkim_elem, "result")
                dkim_selector = _text(dkim_elem, "selector")

            spf_elem = auth.find("spf")
            if spf_elem is not None:
                spf_domain = _text(spf_elem, "domain")
                spf_result = _text(spf_elem, "result")

        records.append({
            "report_id": report_id,
            "org_name": org_name,
            "email": email_addr,
            "extra_contact_info": extra_contact,
            "date_range_begin": date_begin,
            "date_range_end": date_end,
            "domain": domain,
            "adkim": adkim,
            "aspf": aspf,
            "policy_p": policy_p,
            "policy_sp": policy_sp,
            "policy_pct": policy_pct,
            "source_ip": source_ip,
            "count": count,
            "disposition": disposition,
            "dkim_domain": dkim_domain,
            "dkim_result": dkim_result,
            "dkim_selector": dkim_selector,
            "spf_domain": spf_domain,
            "spf_result": spf_result,
            "policy_evaluated_dkim": pe_dkim,
            "policy_evaluated_spf": pe_spf,
            "header_from": header_from,
        })

    logger.info(json.dumps({"event": "dmarc.xml.parsed", "report_id": report_id, "records_count": len(records)}))
    return records


def _write_parquet(records):
    """レコードリストをParquetに変換してS3に出力"""
    if not records:
        return

    table = pa.Table.from_pylist(records, schema=SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")

    # パーティションパス導出
    dt = records[0]["date_range_begin"]
    if isinstance(dt, (int, float)):
        dt = datetime.fromtimestamp(dt, tz=timezone.utc)
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")
    org_name = records[0]["org_name"]
    report_id = records[0]["report_id"]
    safe_org = re.sub(r'[^\w\-.]', '_', org_name or "unknown")

    key = f"{OUTPUT_PREFIX}/year={year}/month={month}/day={day}/{safe_org}__{report_id}.parquet"

    s3.put_object(Bucket=ATHENA_BUCKET, Key=key, Body=buf.getvalue())
    logger.info(json.dumps({"event": "dmarc.parquet.written", "key": key, "records_count": len(records)}))


def _text(parent, tag):
    """XMLエレメントからテキスト取得（None安全）"""
    if parent is None:
        return None
    elem = parent.find(tag)
    return elem.text if elem is not None else None


def _ts(parent, tag):
    """UNIXタイムスタンプ文字列をdatetimeに変換"""
    val = _text(parent, tag)
    if val is None:
        return None
    return datetime.fromtimestamp(int(val), tz=timezone.utc)
