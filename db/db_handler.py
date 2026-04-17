import pymysql
import pandas as pd

# ✅ MySQL DB Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root',
    'database': 'assetgather'
}

# ✅ Get MySQL connection
def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# ✅ Fetch asset info by asset_id
def fetch_asset_info(asset_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, lastItemSeenTime FROM `__item` WHERE serialNo = %s", (asset_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {
                "asset_name": result["name"],
                "last_seen_time": result["lastItemSeenTime"]
            }
    return None

# ✅ Fetch report data between dates
def fetch_report_data(start_date, end_date):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE date BETWEEN %s AND %s", (start_date, end_date))
        results = cursor.fetchall()
        conn.close()
        return results
    return []

# ✅ Fetch last sync status
def fetch_last_sync_details():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sync_logs ORDER BY sync_time DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result
    return None

# ✅ Enriched Track and Trace Report
def fetch_track_and_trace_enriched(connection):
    try:
        cursor = connection.cursor()

        query = """
            SELECT 
                i.itemID,
                MAX(i.name) AS Asset_Name,
                MAX(i.rfID) AS RFID,
                MAX(i.serialNo) AS Serial,
                MAX(i.barcodeID) AS Barcode,
                MAX(i.description) AS Description,
                MAX(it.name) AS Asset_Type,
                MAX(loc.name) AS Location,
                MAX(CASE WHEN a.name = 'Calibration Due' THEN ia.attrval END) AS Calibration_Due,
                MAX(CASE WHEN a.name = 'Attribute 2' THEN ia.attrval END) AS Attribute_2,

                -- ✅ Use MAX() to satisfy ONLY_FULL_GROUP_BY
                CONCAT(
                    FLOOR(TIMESTAMPDIFF(SECOND, MAX(evt_min.min_evt), MAX(evt_max.max_evt)) / 86400), ' Days ',
                    FLOOR(MOD(TIMESTAMPDIFF(SECOND, MAX(evt_min.min_evt), MAX(evt_max.max_evt)), 86400) / 3600), ' Hours'
                ) AS Duration,

                MAX(i.lastItemSeenTime) AS Last_Seen

            FROM __item i
            LEFT JOIN __item_type it ON i.item_typeid = it.id

            LEFT JOIN (
                SELECT ie1.itemID, e.locationID
                FROM __item_event ie1
                INNER JOIN (
                    SELECT itemID, MAX(evtTime) AS max_evt
                    FROM __item_event
                    GROUP BY itemID
                ) ie2 ON ie1.itemID = ie2.itemID AND ie1.evtTime = ie2.max_evt
                LEFT JOIN __event e ON ie1.eventID = e.eventID
            ) latest_event ON i.itemID = latest_event.itemID
            LEFT JOIN __location loc ON latest_event.locationID = loc.locationID

            LEFT JOIN __item_attribute ia ON i.itemID = ia.itemID AND ia.latest = b'1'
            LEFT JOIN __itemtype_attribute ita ON ia.itemTypeAttrId = ita.itemtype_attributeID
            LEFT JOIN __attribute a ON ita.attrKeyId = a.id

            LEFT JOIN (
                SELECT itemID, MIN(evtTime) AS min_evt
                FROM __item_event
                GROUP BY itemID
            ) evt_min ON i.itemID = evt_min.itemID

            LEFT JOIN (
                SELECT itemID, MAX(evtTime) AS max_evt
                FROM __item_event
                GROUP BY itemID
            ) evt_max ON i.itemID = evt_max.itemID

            GROUP BY i.itemID
            ORDER BY i.itemID;
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            row_dict = dict(row)
            row_dict.pop("itemID", None)
            results.append(row_dict)

        return results

    except Exception as e:
        print("❌ MySQL error in fetch_track_and_trace_enriched():", e)
        return []





