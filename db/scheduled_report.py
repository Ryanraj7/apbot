import os
import pandas as pd
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
import pymysql
import warnings
import re

warnings.filterwarnings("ignore", category=UserWarning, module="pandas.io.sql")

# ✅ DB config
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'assetgather',
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)  

# ✅ Create SQLAlchemy engine
def get_db_engine():
    try:
        engine_url = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
        return create_engine(engine_url)
    except Exception as e:
        print(f"❌ Engine creation failed: {e}")
        return None

# ✅ Fetch scheduled reports
def get_all_scheduled_reports():
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT reportName, reportParams FROM __scheduledreports ORDER BY reportId DESC"))
            rows = result.fetchall()
            keys = result.keys()
            return [dict(zip(keys, row)) for row in rows]
    except Exception as e:
        print(f"❌ Error fetching reports: {e}")
        return []

# ✅ Parse XML filters
def parse_report_params(xml_string):
    try:
        root = ET.fromstring(xml_string)
        params = root.find(".//params")
        filters = {}
        for param in params.findall("param"):
            filters[param.attrib["name"]] = param.attrib.get("value", "")
        return filters
    except Exception as e:
        print(f"❌ Error parsing XML: {e}")
        return {}

# ✅ Build SQL query
def build_sql(filters, apply_filters=True):
    where_clauses = []

    if apply_filters:
        if "locations" in filters and filters["locations"]:
            ids = filters["locations"].split(",")
            where_clauses.append(f"loc.locationID IN ({','.join([f'\"{i.strip()}\"' for i in ids])})")

        if "itemTypes" in filters and filters["itemTypes"]:
            ids = filters["itemTypes"].split(",")
            where_clauses.append(f"it.id IN ({','.join([f'\"{i.strip()}\"' for i in ids])})")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"""
        SELECT 
            i.name AS Asset_Name,
            i.rfID AS RFID,
            i.serialNo AS Serial,
            i.barcodeID AS Barcode,
            i.description AS Description,
            it.name AS Asset_Type,
            loc.name AS Location,
            i.lastItemSeenTime AS Last_Seen
        FROM __item i
        LEFT JOIN __item_type it ON i.item_typeid = it.id
        LEFT JOIN (
            SELECT ie.itemID, e.locationID
            FROM __item_event ie
            INNER JOIN (
                SELECT itemID, MAX(evtTime) AS max_evt
                FROM __item_event
                GROUP BY itemID
            ) latest_evt ON ie.itemID = latest_evt.itemID AND ie.evtTime = latest_evt.max_evt
            LEFT JOIN __event e ON ie.eventID = e.eventID
        ) latest_loc ON i.itemID = latest_loc.itemID
        LEFT JOIN __location loc ON latest_loc.locationID = loc.locationID
        {where_sql}
        ORDER BY i.itemID
    """
    return query

# ✅ Save to Excel
def save_report_to_excel(df, report_name):
    safe_name = report_name.replace(" ", "_").lower()
    file_path = os.path.join(STATIC_DIR, f"scheduled_report_{safe_name}.xlsx")
    df.to_excel(file_path, index=False)
    print(f"✅ Report saved: {file_path}")

# ✅ Callable function for integration
def generate_scheduled_reports():
    reports = get_all_scheduled_reports()
    if not reports:
        return "❌ No scheduled reports found."

    engine = get_db_engine()
    if not engine:
        return "❌ Cannot proceed without DB engine."

    summary_lines = []

    for rpt in reports:
        try:
            report_name = rpt["reportName"]
            filters = parse_report_params(rpt["reportParams"])
        except Exception as e:
            print(f"❌ Invalid report format: {rpt} — {e}")
            continue

        print(f"\n📄 Processing Scheduled Report: {report_name}")
        query = build_sql(filters, apply_filters=True)

        try:
            df = pd.read_sql(query, engine)
            header = df.columns.tolist()
            df = df[~df.apply(lambda row: row.tolist() == header, axis=1)]
            df.dropna(how='all', inplace=True)

            if df.empty:
                summary_lines.append(f"⚠️ '{report_name}' returned no data.")
                continue

            print(f"✅ {len(df)} rows returned for report '{report_name}'")
            save_report_to_excel(df, report_name)
            summary_lines.append(f"✅ '{report_name}' generated ({len(df)} rows)")
        except Exception as e:
            print(f"❌ Error generating report '{report_name}': {e}")
            summary_lines.append(f"❌ Error in '{report_name}': {str(e)}")

    if summary_lines:
      clean_lines = [re.sub(r"<br\s*/?>", "", line).strip() for line in summary_lines]
      numbered = [f"{i+1}. {line}" for i, line in enumerate(clean_lines)]
      print("📤 Final return:\n" + "🗂️Scheduled Reports Generated\n" + "\n".join(numbered))

    return "🗂️ Scheduled Reports Generated:\n" + "\n".join(numbered)
