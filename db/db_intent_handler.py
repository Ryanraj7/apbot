import re
import pandas as pd
from .db_handler import (
    get_db_connection,
    fetch_asset_info,
    fetch_report_data,
    fetch_last_sync_details,
    fetch_track_and_trace_enriched
)

# ✅ Picklist fetch function
def fetch_picklist_titles(conn):
    try:
        print("🔍 Fetching picklists...")
        with conn.cursor() as cursor:
            cursor.execute("SELECT itemListId, itemListName FROM __item_list ORDER BY itemListId")
            rows = cursor.fetchall()
            print(f"📦 Got {len(rows)} picklist rows")

            if not rows:
                return "🗂️ No picklists found."

            return "🗂️ You have the following picklists:<br>" + "".join(
                f"{idx}. {row['itemListName']}<br>" for idx, row in enumerate(rows, 1)
            )
    except Exception as e:
        print(f"❌ Exception in picklist: {e}")
        return f"❌ Error fetching picklists: {e}"

# ✅ Empty locations
def fetch_empty_locations(conn):
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT loc.name AS Location
                FROM __location loc
                WHERE loc.locationID NOT IN (
                    SELECT DISTINCT latest.locationID
                    FROM (
                        SELECT e.locationID
                        FROM __item_event ie
                        INNER JOIN (
                            SELECT itemID, MAX(evtTime) AS max_evt
                            FROM __item_event
                            GROUP BY itemID
                        ) latest_evt ON ie.itemID = latest_evt.itemID AND ie.evtTime = latest_evt.max_evt
                        LEFT JOIN __event e ON ie.eventID = e.eventID
                    ) latest
                    WHERE latest.locationID IS NOT NULL
                )
                ORDER BY loc.name
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                return "📦 All locations currently have assets."

            return "📦 Empty Locations:<br>" + "".join(
                f"{idx}. {row['Location']}<br>" for idx, row in enumerate(rows, 1)
            )
    except Exception as e:
        return f"❌ Error fetching empty locations: {e}"

# ✅ Top locations
def fetch_top_locations_this_month(conn, limit=10):
    try:
        with conn.cursor() as cursor:
            query = f"""
                SELECT 
                    loc.name AS Location,
                    COUNT(*) AS Movement_Count
                FROM __item_event ie
                INNER JOIN __event e ON ie.eventID = e.eventID
                INNER JOIN __location loc ON e.locationID = loc.locationID
                WHERE e.evtTime >= (NOW() - INTERVAL 30 DAY)
                  AND e.locationID IS NOT NULL
                GROUP BY e.locationID
                ORDER BY Movement_Count DESC
                LIMIT {limit}
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            if not rows:
                return "📍 No recent activity in the last 30 days."

            return "📍 Top Locations (Last 30 Days):<br>" + "".join(
                f"{idx}. {row['Location']} – {row['Movement_Count']} movements<br>"
                for idx, row in enumerate(rows, 1)
            )
    except Exception as e:
        return f"❌ Error fetching top locations: {e}"

# ✅ Intent map for direct functions
intent_function_map = {
    "get asset details": fetch_asset_info,
    "generate report": fetch_report_data,
    "last sync status": fetch_last_sync_details,
}

# ✅ Parameter extractor
def extract_parameters(intent, msg):
    if intent == "get asset details":
        match = re.search(r"\b(\d+)\b", msg)
        return [match.group(1)] if match else None

    elif intent == "generate report":
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", msg)
        return dates if len(dates) == 2 else None

    return [] if intent in ["last sync status", "track and trace", "list picklists", "list empty locations", "top locations this month"] else None

# ✅ Formatter
def format_response(intent, result):
    if isinstance(result, list):
        if not result:
            return "No records found."

        if intent == "top locations this month":
            return "\n".join(
                [f"📍 Top Locations (Last 30 Days):"] +
                [f"{i+1}. {row.get('location') or row.get('Location')} – {row.get('event_count') or row.get('Count')} movements"
                 for i, row in enumerate(result)]
            )

        elif intent == "list empty locations":
            return "📦 Empty Locations:\n" + "\n".join(f"{i+1}. {row}" for i, row in enumerate(result))

        elif intent == "list picklists":
            return "📋 Available Picklists:\n" + "\n".join(f"{i+1}. {row}" for i, row in enumerate(result))

        return "\n".join(str(row) for row in result)

    return str(result)

# ✅ Main DB intent handler
def handle_db_intent(intent, user_message, raw=False):
    try:
        conn = None

        if intent in ["track and trace", "list picklists", "list empty locations", "top locations this month"]:
            conn = get_db_connection()
            if not conn:
                return "❌ Database connection error."

            if intent == "track and trace":
                result = fetch_track_and_trace_enriched(conn)
            elif intent == "list picklists":
                result = fetch_picklist_titles(conn)
            elif intent == "list empty locations":
                result = fetch_empty_locations(conn)
            elif intent == "top locations this month":
                result = fetch_top_locations_this_month(conn)
            conn.close()

        else:
            handler = intent_function_map.get(intent)
            if not handler:
                return None

            params = extract_parameters(intent, user_message)
            result = handler(*params) if params else handler()

        return result if raw else format_response(intent, result)

    except Exception as e:
        return f"❌ Error: {str(e)}"
