 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/static/index.html
index 0000000000000000000000000000000000000000..dfc18756ae16d8015dba73b20eb8437d6f0171af 100644
--- a//dev/null
+++ b/static/index.html
@@ -0,0 +1,220 @@
+<!DOCTYPE html>
+<html lang="en">
+<head>
+    <meta charset="UTF-8">
+    <meta name="viewport" content="width=device-width, initial-scale=1.0">
+    <title>Inventory Intelligence Dashboard</title>
+    <link rel="stylesheet" href="/styles.css">
+</head>
+<body>
+<header class="app-header" role="banner">
+    <div class="brand">
+        <span class="brand-icon" aria-hidden="true">📦</span>
+        <h1>Inventory Intelligence</h1>
+    </div>
+    <nav aria-label="Primary navigation">
+        <ul class="nav-links">
+            <li><a href="#dashboard" class="nav-link">Dashboard</a></li>
+            <li><a href="#inventory" class="nav-link">Inventory</a></li>
+            <li><a href="#usage" class="nav-link">Usage Tracking</a></li>
+            <li><a href="#shopping" class="nav-link">Shopping List</a></li>
+        </ul>
+    </nav>
+</header>
+<main>
+    <section id="dashboard" class="panel" aria-labelledby="dashboard-title">
+        <div class="panel-header">
+            <h2 id="dashboard-title">Dashboard Overview</h2>
+            <p class="panel-subtitle">Real-time performance and alerts</p>
+        </div>
+        <div class="dashboard-grid">
+            <article class="metric-card" aria-live="polite">
+                <h3>Total Inventory Value</h3>
+                <p class="metric" id="metric-value">$0.00</p>
+            </article>
+            <article class="metric-card">
+                <h3>Total Units</h3>
+                <p class="metric" id="metric-units">0</p>
+            </article>
+            <article class="metric-card warning" id="metric-low-stock">
+                <h3>Low Stock Items</h3>
+                <p class="metric">0</p>
+            </article>
+            <article class="metric-card info" id="metric-overstock">
+                <h3>Overstocked Items</h3>
+                <p class="metric">0</p>
+            </article>
+        </div>
+        <div class="charts-grid">
+            <figure class="chart-card">
+                <figcaption>Inventory Distribution</figcaption>
+                <canvas id="stock-distribution" aria-label="Inventory distribution chart" role="img"></canvas>
+            </figure>
+            <figure class="chart-card">
+                <figcaption>Stock Health</figcaption>
+                <canvas id="stock-health" aria-label="Stock health chart" role="img"></canvas>
+            </figure>
+        </div>
+        <div class="activity-grid">
+            <section aria-labelledby="recent-activity-title" class="activity-panel">
+                <h3 id="recent-activity-title">Recent Activity</h3>
+                <ul id="activity-feed" class="activity-feed" aria-live="polite"></ul>
+            </section>
+            <section aria-labelledby="recent-usage-title" class="activity-panel">
+                <h3 id="recent-usage-title">Recent Usage</h3>
+                <ul id="usage-feed" class="activity-feed"></ul>
+            </section>
+        </div>
+    </section>
+
+    <section id="inventory" class="panel" aria-labelledby="inventory-title">
+        <div class="panel-header">
+            <h2 id="inventory-title">Inventory Management</h2>
+            <p class="panel-subtitle">Track stock levels, costs, and alerts</p>
+        </div>
+        <div class="form-grid">
+            <form id="add-item-form" class="card" aria-describedby="add-item-help">
+                <h3>Add New Item</h3>
+                <p id="add-item-help">Complete all fields to add inventory items. Attributes should be meaningful descriptors.</p>
+                <div class="input-group">
+                    <label for="add-name">Item Name</label>
+                    <input id="add-name" name="name" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-barcode">Barcode / ID</label>
+                    <input id="add-barcode" name="barcode" required aria-describedby="barcode-hint">
+                    <span id="barcode-hint" class="input-hint">Scan or enter manually.</span>
+                </div>
+                <div class="input-group">
+                    <label for="add-brand">Brand</label>
+                    <input id="add-brand" name="brand" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-type">Item Type</label>
+                    <input id="add-type" name="item_type" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-unit-size">Unit Size</label>
+                    <input id="add-unit-size" name="unit_size" placeholder="e.g. 500ml" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-total-cost">Total Cost</label>
+                    <input id="add-total-cost" name="total_cost" type="number" min="0" step="0.01" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-stock">Initial Stock Level</label>
+                    <input id="add-stock" name="stock_level" type="number" min="1" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-min">Minimum Threshold</label>
+                    <input id="add-min" name="min_stock" type="number" min="0" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-max">Maximum Threshold</label>
+                    <input id="add-max" name="max_stock" type="number" min="1" required>
+                </div>
+                <div class="input-group">
+                    <label for="add-attributes">Attributes</label>
+                    <textarea id="add-attributes" name="attributes" rows="3" placeholder="key: value"></textarea>
+                </div>
+                <button type="submit" class="primary">Add Item</button>
+            </form>
+            <form id="adjust-form" class="card">
+                <h3>Adjust Stock</h3>
+                <div class="input-group">
+                    <label for="adjust-barcode">Barcode / ID</label>
+                    <input id="adjust-barcode" name="barcode" required>
+                </div>
+                <div class="input-group">
+                    <label for="adjust-delta">Quantity Change</label>
+                    <input id="adjust-delta" name="delta" type="number" required aria-describedby="delta-hint">
+                    <span id="delta-hint" class="input-hint">Use positive numbers to add stock, negative to deduct.</span>
+                </div>
+                <div class="input-group">
+                    <label for="adjust-reason">Reason</label>
+                    <input id="adjust-reason" name="reason" required>
+                </div>
+                <button type="submit" class="secondary">Update Stock</button>
+            </form>
+        </div>
+        <div class="table-container" role="region" aria-labelledby="inventory-table-title" tabindex="0">
+            <h3 id="inventory-table-title">Inventory Items</h3>
+            <table class="data-table">
+                <thead>
+                    <tr>
+                        <th scope="col">Barcode</th>
+                        <th scope="col">Name</th>
+                        <th scope="col">Type</th>
+                        <th scope="col">Brand</th>
+                        <th scope="col">Unit Size</th>
+                        <th scope="col">Unit Cost</th>
+                        <th scope="col">Stock</th>
+                        <th scope="col">Value</th>
+                        <th scope="col">Status</th>
+                    </tr>
+                </thead>
+                <tbody id="inventory-body"></tbody>
+            </table>
+        </div>
+    </section>
+
+    <section id="usage" class="panel" aria-labelledby="usage-title">
+        <div class="panel-header">
+            <h2 id="usage-title">Usage Tracking</h2>
+            <p class="panel-subtitle">Monitor client usage and deduct inventory automatically</p>
+        </div>
+        <form id="usage-form" class="card">
+            <div class="input-group">
+                <label for="usage-client">Client / Project Name</label>
+                <input id="usage-client" name="client_name" required>
+            </div>
+            <div class="input-group">
+                <label for="usage-date">Usage Date</label>
+                <input id="usage-date" name="usage_date" type="date" required>
+            </div>
+            <div class="input-group">
+                <label for="usage-before">Before State</label>
+                <textarea id="usage-before" name="before_state" rows="2" required></textarea>
+            </div>
+            <div class="input-group">
+                <label for="usage-after">After State</label>
+                <textarea id="usage-after" name="after_state" rows="2" required></textarea>
+            </div>
+            <fieldset class="usage-items">
+                <legend>Items Used</legend>
+                <div id="usage-items-container"></div>
+                <button type="button" class="tertiary" id="add-usage-item">Add Item</button>
+            </fieldset>
+            <div class="usage-summary" aria-live="polite">
+                <p>Total cost: <span id="usage-total-cost">$0.00</span></p>
+            </div>
+            <button type="submit" class="primary">Record Usage</button>
+        </form>
+    </section>
+
+    <section id="shopping" class="panel" aria-labelledby="shopping-title">
+        <div class="panel-header">
+            <h2 id="shopping-title">Shopping List</h2>
+            <p class="panel-subtitle">Items needing replenishment</p>
+        </div>
+        <div class="table-container" role="region" aria-labelledby="shopping-table-title" tabindex="0">
+            <h3 id="shopping-table-title">Pending Purchases</h3>
+            <table class="data-table">
+                <thead>
+                    <tr>
+                        <th scope="col">Item</th>
+                        <th scope="col">Barcode</th>
+                        <th scope="col">Brand</th>
+                        <th scope="col">Type</th>
+                        <th scope="col">Added</th>
+                    </tr>
+                </thead>
+                <tbody id="shopping-body"></tbody>
+            </table>
+        </div>
+    </section>
+</main>
+<div class="toast" role="alert" aria-live="assertive" aria-atomic="true" hidden></div>
+<script src="/app.js" defer></script>
+</body>
+</html>
 
EOF
)
