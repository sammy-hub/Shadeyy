 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/app.py
index 0000000000000000000000000000000000000000..976a0949751f8c8bd4b037feb511d115e78c29f0 100644
--- a//dev/null
+++ b/app.py
@@ -0,0 +1,618 @@
+import json
+import os
+import sqlite3
+from datetime import datetime
+from http import HTTPStatus
+from http.server import BaseHTTPRequestHandler, HTTPServer
+from pathlib import Path
+from urllib.parse import urlparse
+
+BASE_DIR = Path(__file__).resolve().parent
+DB_PATH = BASE_DIR / "inventory.db"
+STATIC_DIR = BASE_DIR / "static"
+
+
+def get_connection():
+    conn = sqlite3.connect(DB_PATH)
+    conn.row_factory = sqlite3.Row
+    return conn
+
+
+def initialize_database():
+    conn = get_connection()
+    try:
+        cursor = conn.cursor()
+        cursor.execute(
+            """
+            CREATE TABLE IF NOT EXISTS inventory_items (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                barcode TEXT UNIQUE NOT NULL,
+                name TEXT NOT NULL,
+                brand TEXT NOT NULL,
+                item_type TEXT NOT NULL,
+                attributes TEXT NOT NULL,
+                unit_size TEXT NOT NULL,
+                unit_cost REAL NOT NULL,
+                stock_level INTEGER NOT NULL,
+                min_stock INTEGER NOT NULL,
+                max_stock INTEGER NOT NULL,
+                created_at TEXT NOT NULL,
+                updated_at TEXT NOT NULL
+            )
+            """
+        )
+        cursor.execute(
+            """
+            CREATE TABLE IF NOT EXISTS usage_records (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                client_name TEXT NOT NULL,
+                usage_date TEXT NOT NULL,
+                before_state TEXT NOT NULL,
+                after_state TEXT NOT NULL,
+                total_cost REAL NOT NULL,
+                created_at TEXT NOT NULL
+            )
+            """
+        )
+        cursor.execute(
+            """
+            CREATE TABLE IF NOT EXISTS usage_items (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                usage_id INTEGER NOT NULL,
+                item_id INTEGER NOT NULL,
+                amount_used INTEGER NOT NULL,
+                cost REAL NOT NULL,
+                FOREIGN KEY (usage_id) REFERENCES usage_records(id) ON DELETE CASCADE,
+                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE
+            )
+            """
+        )
+        cursor.execute(
+            """
+            CREATE TABLE IF NOT EXISTS shopping_list (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                item_id INTEGER NOT NULL UNIQUE,
+                added_at TEXT NOT NULL,
+                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE
+            )
+            """
+        )
+        cursor.execute(
+            """
+            CREATE TABLE IF NOT EXISTS inventory_movements (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                item_id INTEGER NOT NULL,
+                change_amount INTEGER NOT NULL,
+                reason TEXT NOT NULL,
+                created_at TEXT NOT NULL,
+                FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE
+            )
+            """
+        )
+        conn.commit()
+    finally:
+        conn.close()
+
+
+def json_response(handler: BaseHTTPRequestHandler, payload, status=HTTPStatus.OK):
+    response_data = json.dumps(payload).encode("utf-8")
+    handler.send_response(status.value)
+    handler.send_header("Content-Type", "application/json")
+    handler.send_header("Content-Length", str(len(response_data)))
+    handler.end_headers()
+    handler.wfile.write(response_data)
+
+
+def error_response(handler: BaseHTTPRequestHandler, message: str, status=HTTPStatus.BAD_REQUEST):
+    json_response(handler, {"error": message}, status)
+
+
+def parse_request_body(handler: BaseHTTPRequestHandler):
+    length = int(handler.headers.get("Content-Length", "0"))
+    if length == 0:
+        return {}
+    body = handler.rfile.read(length)
+    try:
+        return json.loads(body.decode("utf-8"))
+    except json.JSONDecodeError as exc:
+        raise ValueError(f"Invalid JSON payload: {exc}")
+
+
+def serialize_item(row):
+    attributes = json.loads(row["attributes"]) if row["attributes"] else {}
+    stock_value = row["unit_cost"] * row["stock_level"]
+    now_stock = row["stock_level"]
+    status = "ok"
+    if now_stock <= row["min_stock"]:
+        status = "low"
+    elif now_stock >= row["max_stock"]:
+        status = "overstock"
+    return {
+        "id": row["id"],
+        "barcode": row["barcode"],
+        "name": row["name"],
+        "brand": row["brand"],
+        "item_type": row["item_type"],
+        "attributes": attributes,
+        "unit_size": row["unit_size"],
+        "unit_cost": row["unit_cost"],
+        "stock_level": row["stock_level"],
+        "min_stock": row["min_stock"],
+        "max_stock": row["max_stock"],
+        "stock_value": stock_value,
+        "status": status,
+        "created_at": row["created_at"],
+        "updated_at": row["updated_at"],
+    }
+
+
+def add_movement(conn, item_id: int, change: int, reason: str):
+    cursor = conn.cursor()
+    cursor.execute(
+        """
+        INSERT INTO inventory_movements (item_id, change_amount, reason, created_at)
+        VALUES (?, ?, ?, ?)
+        """,
+        (item_id, change, reason, datetime.utcnow().isoformat()),
+    )
+
+
+def ensure_shopping_list_entry(conn, item_id: int):
+    cursor = conn.cursor()
+    cursor.execute("SELECT id FROM shopping_list WHERE item_id = ?", (item_id,))
+    if cursor.fetchone() is None:
+        cursor.execute(
+            "INSERT INTO shopping_list (item_id, added_at) VALUES (?, ?)",
+            (item_id, datetime.utcnow().isoformat()),
+        )
+
+
+def remove_shopping_list_entry(conn, item_id: int):
+    cursor = conn.cursor()
+    cursor.execute("DELETE FROM shopping_list WHERE item_id = ?", (item_id,))
+
+
+class InventoryRequestHandler(BaseHTTPRequestHandler):
+    server_version = "InventoryServer/1.0"
+
+    def do_OPTIONS(self):  # pragma: no cover - placeholder for future extension
+        self.send_response(HTTPStatus.NO_CONTENT)
+        self.send_header("Allow", "GET, POST, PUT, OPTIONS")
+        self.send_header("Access-Control-Allow-Origin", "*")
+        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
+        self.send_header("Access-Control-Allow-Headers", "Content-Type")
+        self.end_headers()
+
+    def do_GET(self):
+        parsed = urlparse(self.path)
+        if parsed.path.startswith("/api/"):
+            self.handle_api_get(parsed)
+        else:
+            self.serve_static(parsed.path)
+
+    def do_POST(self):
+        parsed = urlparse(self.path)
+        if not parsed.path.startswith("/api/"):
+            return error_response(self, "Unsupported endpoint", HTTPStatus.NOT_FOUND)
+        try:
+            payload = parse_request_body(self)
+        except ValueError as exc:
+            return error_response(self, str(exc))
+        if parsed.path == "/api/items":
+            return self.create_item(payload)
+        if parsed.path == "/api/items/adjust":
+            return self.adjust_item(payload)
+        if parsed.path == "/api/usage":
+            return self.record_usage(payload)
+        return error_response(self, "Unknown endpoint", HTTPStatus.NOT_FOUND)
+
+    def do_PUT(self):
+        parsed = urlparse(self.path)
+        if parsed.path == "/api/items":
+            try:
+                payload = parse_request_body(self)
+            except ValueError as exc:
+                return error_response(self, str(exc))
+            return self.update_item(payload)
+        return error_response(self, "Unknown endpoint", HTTPStatus.NOT_FOUND)
+
+    def serve_static(self, path: str):
+        target = STATIC_DIR / "index.html"
+        if path != "/":
+            target = (STATIC_DIR / path.lstrip("/")).resolve()
+            if not str(target).startswith(str(STATIC_DIR.resolve())):
+                return error_response(self, "Forbidden", HTTPStatus.FORBIDDEN)
+            if not target.exists() or not target.is_file():
+                target = STATIC_DIR / "index.html"
+        if not target.exists():
+            return error_response(self, "Static asset not found", HTTPStatus.NOT_FOUND)
+        if target.suffix == ".html":
+            content_type = "text/html; charset=utf-8"
+        elif target.suffix == ".css":
+            content_type = "text/css; charset=utf-8"
+        elif target.suffix == ".js":
+            content_type = "application/javascript; charset=utf-8"
+        elif target.suffix == ".json":
+            content_type = "application/json; charset=utf-8"
+        elif target.suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
+            content_type = f"image/{target.suffix.lstrip('.')}"
+        elif target.suffix == ".ico":
+            content_type = "image/x-icon"
+        else:
+            content_type = "application/octet-stream"
+        with open(target, "rb") as file_obj:
+            data = file_obj.read()
+        self.send_response(HTTPStatus.OK)
+        self.send_header("Content-Type", content_type)
+        self.send_header("Content-Length", str(len(data)))
+        self.end_headers()
+        self.wfile.write(data)
+
+    def handle_api_get(self, parsed):
+        if parsed.path == "/api/items":
+            return self.list_items()
+        if parsed.path == "/api/dashboard":
+            return self.dashboard_summary()
+        if parsed.path == "/api/shopping-list":
+            return self.get_shopping_list()
+        if parsed.path == "/api/activity":
+            return self.get_activity()
+        return error_response(self, "Unknown endpoint", HTTPStatus.NOT_FOUND)
+
+    def list_items(self):
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute("SELECT * FROM inventory_items ORDER BY name")
+            items = [serialize_item(row) for row in cursor.fetchall()]
+            json_response(self, {"items": items})
+        finally:
+            conn.close()
+
+    def create_item(self, payload):
+        required = {
+            "barcode",
+            "name",
+            "brand",
+            "item_type",
+            "attributes",
+            "unit_size",
+            "total_cost",
+            "stock_level",
+            "min_stock",
+            "max_stock",
+        }
+        missing = [field for field in required if field not in payload]
+        if missing:
+            return error_response(self, f"Missing fields: {', '.join(missing)}")
+        try:
+            stock_level = int(payload["stock_level"])
+            min_stock = int(payload["min_stock"])
+            max_stock = int(payload["max_stock"])
+            total_cost = float(payload["total_cost"])
+        except (TypeError, ValueError):
+            return error_response(self, "Invalid numeric values provided")
+        if stock_level <= 0:
+            return error_response(self, "Stock level must be greater than zero")
+        if min_stock < 0 or max_stock <= 0 or max_stock < min_stock:
+            return error_response(self, "Invalid stock thresholds")
+        unit_cost = round(total_cost / stock_level, 4)
+        attributes = payload["attributes"]
+        if isinstance(attributes, dict):
+            attributes_json = json.dumps(attributes)
+        else:
+            return error_response(self, "Attributes must be an object")
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            now = datetime.utcnow().isoformat()
+            cursor.execute(
+                """
+                INSERT INTO inventory_items (
+                    barcode, name, brand, item_type, attributes, unit_size,
+                    unit_cost, stock_level, min_stock, max_stock, created_at, updated_at
+                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
+                """,
+                (
+                    payload["barcode"],
+                    payload["name"],
+                    payload["brand"],
+                    payload["item_type"],
+                    attributes_json,
+                    payload["unit_size"],
+                    unit_cost,
+                    stock_level,
+                    min_stock,
+                    max_stock,
+                    now,
+                    now,
+                ),
+            )
+            item_id = cursor.lastrowid
+            add_movement(conn, item_id, stock_level, "Initial stock")
+            conn.commit()
+        except sqlite3.IntegrityError:
+            conn.rollback()
+            return error_response(self, "Item with the provided barcode already exists", HTTPStatus.CONFLICT)
+        finally:
+            conn.close()
+        json_response(self, {"message": "Item created successfully"}, HTTPStatus.CREATED)
+
+    def adjust_item(self, payload):
+        for field in ("barcode", "delta", "reason"):
+            if field not in payload:
+                return error_response(self, f"Missing field: {field}")
+        try:
+            delta = int(payload["delta"])
+        except (TypeError, ValueError):
+            return error_response(self, "Delta must be an integer")
+        if delta == 0:
+            return error_response(self, "Delta cannot be zero")
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute("SELECT * FROM inventory_items WHERE barcode = ?", (payload["barcode"],))
+            row = cursor.fetchone()
+            if row is None:
+                return error_response(self, "Item not found", HTTPStatus.NOT_FOUND)
+            new_stock = row["stock_level"] + delta
+            if new_stock < 0:
+                return error_response(self, "Insufficient stock for the adjustment", HTTPStatus.CONFLICT)
+            now = datetime.utcnow().isoformat()
+            cursor.execute(
+                """
+                UPDATE inventory_items
+                SET stock_level = ?, updated_at = ?
+                WHERE id = ?
+                """,
+                (new_stock, now, row["id"]),
+            )
+            add_movement(conn, row["id"], delta, payload["reason"])
+            if new_stock == 0:
+                ensure_shopping_list_entry(conn, row["id"])
+            else:
+                remove_shopping_list_entry(conn, row["id"])
+            conn.commit()
+        finally:
+            conn.close()
+        json_response(self, {"message": "Stock adjusted", "new_stock": new_stock})
+
+    def record_usage(self, payload):
+        required = {"client_name", "usage_date", "before_state", "after_state", "items"}
+        missing = [field for field in required if field not in payload]
+        if missing:
+            return error_response(self, f"Missing fields: {', '.join(missing)}")
+        items = payload["items"]
+        if not isinstance(items, list) or not items:
+            return error_response(self, "Items must be a non-empty list")
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cost_total = 0.0
+            item_updates = []
+            for entry in items:
+                if "barcode" not in entry or "amount" not in entry:
+                    conn.rollback()
+                    return error_response(self, "Each usage item must include barcode and amount")
+                try:
+                    amount = int(entry["amount"])
+                except (TypeError, ValueError):
+                    conn.rollback()
+                    return error_response(self, "Item amount must be an integer")
+                if amount <= 0:
+                    conn.rollback()
+                    return error_response(self, "Item amount must be greater than zero")
+                cursor.execute("SELECT * FROM inventory_items WHERE barcode = ?", (entry["barcode"],))
+                item_row = cursor.fetchone()
+                if item_row is None:
+                    conn.rollback()
+                    return error_response(self, f"Item with barcode {entry['barcode']} not found", HTTPStatus.NOT_FOUND)
+                if item_row["stock_level"] < amount:
+                    conn.rollback()
+                    return error_response(self, f"Insufficient stock for {item_row['name']}", HTTPStatus.CONFLICT)
+                cost = amount * item_row["unit_cost"]
+                cost_total += cost
+                item_updates.append((item_row, amount, cost))
+            now = datetime.utcnow().isoformat()
+            cursor.execute(
+                """
+                INSERT INTO usage_records (client_name, usage_date, before_state, after_state, total_cost, created_at)
+                VALUES (?, ?, ?, ?, ?, ?)
+                """,
+                (
+                    payload["client_name"],
+                    payload["usage_date"],
+                    payload["before_state"],
+                    payload["after_state"],
+                    round(cost_total, 2),
+                    now,
+                ),
+            )
+            usage_id = cursor.lastrowid
+            for item_row, amount, cost in item_updates:
+                new_stock = item_row["stock_level"] - amount
+                cursor.execute(
+                    """
+                    UPDATE inventory_items
+                    SET stock_level = ?, updated_at = ?
+                    WHERE id = ?
+                    """,
+                    (new_stock, now, item_row["id"]),
+                )
+                cursor.execute(
+                    """
+                    INSERT INTO usage_items (usage_id, item_id, amount_used, cost)
+                    VALUES (?, ?, ?, ?)
+                    """,
+                    (usage_id, item_row["id"], amount, round(cost, 2)),
+                )
+                add_movement(conn, item_row["id"], -amount, f"Usage: {payload['client_name']}")
+                if new_stock == 0:
+                    ensure_shopping_list_entry(conn, item_row["id"])
+                else:
+                    remove_shopping_list_entry(conn, item_row["id"])
+            conn.commit()
+        finally:
+            conn.close()
+        json_response(self, {"message": "Usage recorded", "total_cost": round(cost_total, 2)})
+
+    def update_item(self, payload):
+        required = {"barcode"}
+        missing = [field for field in required if field not in payload]
+        if missing:
+            return error_response(self, f"Missing fields: {', '.join(missing)}")
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute("SELECT * FROM inventory_items WHERE barcode = ?", (payload["barcode"],))
+            row = cursor.fetchone()
+            if row is None:
+                return error_response(self, "Item not found", HTTPStatus.NOT_FOUND)
+            updates = {}
+            allowed_fields = {"name", "brand", "item_type", "attributes", "unit_size", "unit_cost", "min_stock", "max_stock"}
+            for key in allowed_fields:
+                if key in payload:
+                    updates[key] = payload[key]
+            if not updates:
+                return error_response(self, "No valid fields to update")
+            if "attributes" in updates:
+                if isinstance(updates["attributes"], dict):
+                    updates["attributes"] = json.dumps(updates["attributes"])
+                else:
+                    return error_response(self, "Attributes must be an object")
+            if "unit_cost" in updates:
+                try:
+                    updates["unit_cost"] = float(updates["unit_cost"])
+                except (TypeError, ValueError):
+                    return error_response(self, "Unit cost must be numeric")
+            if "min_stock" in updates:
+                try:
+                    updates["min_stock"] = int(updates["min_stock"])
+                except (TypeError, ValueError):
+                    return error_response(self, "Minimum stock must be integer")
+            if "max_stock" in updates:
+                try:
+                    updates["max_stock"] = int(updates["max_stock"])
+                except (TypeError, ValueError):
+                    return error_response(self, "Maximum stock must be integer")
+            if "min_stock" in updates or "max_stock" in updates:
+                min_stock = updates.get("min_stock", row["min_stock"])
+                max_stock = updates.get("max_stock", row["max_stock"])
+                if min_stock < 0 or max_stock <= 0 or max_stock < min_stock:
+                    return error_response(self, "Invalid stock thresholds")
+            set_clause = ", ".join(f"{key} = ?" for key in updates)
+            values = list(updates.values())
+            values.append(datetime.utcnow().isoformat())
+            values.append(row["id"])
+            cursor.execute(
+                f"UPDATE inventory_items SET {set_clause}, updated_at = ? WHERE id = ?",
+                values,
+            )
+            conn.commit()
+        finally:
+            conn.close()
+        json_response(self, {"message": "Item updated"})
+
+    def dashboard_summary(self):
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute("SELECT * FROM inventory_items")
+            items = [serialize_item(row) for row in cursor.fetchall()]
+            total_value = sum(item["stock_value"] for item in items)
+            total_units = sum(item["stock_level"] for item in items)
+            low_stock = [item for item in items if item["status"] == "low"]
+            overstock = [item for item in items if item["status"] == "overstock"]
+            cursor.execute(
+                """
+                SELECT ur.id, ur.client_name, ur.usage_date, ur.total_cost, ur.created_at,
+                       GROUP_CONCAT(ii.name || ' x' || ui.amount_used, '; ') AS details
+                FROM usage_records ur
+                JOIN usage_items ui ON ui.usage_id = ur.id
+                JOIN inventory_items ii ON ui.item_id = ii.id
+                GROUP BY ur.id
+                ORDER BY ur.created_at DESC
+                LIMIT 10
+                """
+            )
+            recent_usage = [dict(row) for row in cursor.fetchall()]
+            cursor.execute(
+                """
+                SELECT im.id, im.change_amount, im.reason, im.created_at, ii.name
+                FROM inventory_movements im
+                JOIN inventory_items ii ON im.item_id = ii.id
+                ORDER BY im.created_at DESC
+                LIMIT 10
+                """
+            )
+            movements = [dict(row) for row in cursor.fetchall()]
+            json_response(
+                self,
+                {
+                    "total_value": round(total_value, 2),
+                    "total_units": total_units,
+                    "items": items,
+                    "low_stock": low_stock,
+                    "overstock": overstock,
+                    "recent_usage": recent_usage,
+                    "movements": movements,
+                },
+            )
+        finally:
+            conn.close()
+
+    def get_shopping_list(self):
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute(
+                """
+                SELECT sl.id, sl.added_at, ii.name, ii.barcode, ii.brand, ii.item_type
+                FROM shopping_list sl
+                JOIN inventory_items ii ON sl.item_id = ii.id
+                ORDER BY sl.added_at DESC
+                """
+            )
+            entries = [dict(row) for row in cursor.fetchall()]
+            json_response(self, {"items": entries})
+        finally:
+            conn.close()
+
+    def get_activity(self):
+        conn = get_connection()
+        try:
+            cursor = conn.cursor()
+            cursor.execute(
+                """
+                SELECT im.id, im.change_amount, im.reason, im.created_at, ii.name
+                FROM inventory_movements im
+                JOIN inventory_items ii ON im.item_id = ii.id
+                ORDER BY im.created_at DESC
+                LIMIT 25
+                """
+            )
+            movements = [dict(row) for row in cursor.fetchall()]
+            json_response(self, {"movements": movements})
+        finally:
+            conn.close()
+
+    def log_message(self, format, *args):
+        return
+
+
+def run_server():
+    initialize_database()
+    port = int(os.environ.get("PORT", "8000"))
+    address = ("0.0.0.0", port)
+    httpd = HTTPServer(address, InventoryRequestHandler)
+    print(f"Inventory management server running on http://{address[0]}:{address[1]}")
+    try:
+        httpd.serve_forever()
+    except KeyboardInterrupt:
+        pass
+    finally:
+        httpd.server_close()
+
+
+if __name__ == "__main__":
+    run_server()
 
EOF
)
