const state = {
    items: [],
    shoppingList: [],
    usageItems: [],
    charts: {},
};

const toast = document.querySelector('.toast');

function showToast(message, variant = 'info') {
    toast.textContent = message;
    toast.className = `toast show ${variant}`;
    toast.hidden = false;
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.hidden = true;
            toast.className = 'toast';
        }, 250);
    }, 3200);
}

async function request(path, options = {}) {
    const response = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || error.message || 'Request failed');
    }
    return response.json();
}

function parseAttributes(text) {
    const attributes = {};
    text
        .split(/\n|,/)
        .map((line) => line.trim())
        .filter(Boolean)
        .forEach((line) => {
            const [key, ...rest] = line.split(':');
            if (key && rest.length) {
                attributes[key.trim()] = rest.join(':').trim();
            }
        });
    return attributes;
}

function formatCurrency(value) {
    return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
    }).format(Number(value || 0));
}

function renderInventory(items) {
    const tbody = document.getElementById('inventory-body');
    tbody.innerHTML = '';
    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.barcode}</td>
            <td>
                <div class="item-name">${item.name}</div>
                <div class="item-meta">${Object.entries(item.attributes || {})
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(' • ')}</div>
            </td>
            <td>${item.item_type}</td>
            <td>${item.brand}</td>
            <td>${item.unit_size}</td>
            <td>${formatCurrency(item.unit_cost)}</td>
            <td>${item.stock_level}</td>
            <td>${formatCurrency(item.stock_value)}</td>
            <td><span class="badge ${item.status}">${item.status === 'low' ? 'Low Stock' : item.status === 'overstock' ? 'Overstock' : 'Healthy'}</span></td>
        `;
        fragment.appendChild(row);
    });
    tbody.appendChild(fragment);
}

function renderShoppingList(items) {
    const tbody = document.getElementById('shopping-body');
    tbody.innerHTML = '';
    const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    items.forEach((item) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.name}</td>
            <td>${item.barcode}</td>
            <td>${item.brand}</td>
            <td>${item.item_type}</td>
            <td>${formatter.format(new Date(item.added_at))}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderActivity(entries) {
    const container = document.getElementById('activity-feed');
    container.innerHTML = '';
    const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    entries.forEach((entry) => {
        const li = document.createElement('li');
        const change = entry.change_amount > 0 ? `+${entry.change_amount}` : entry.change_amount;
        li.innerHTML = `
            <strong>${entry.name}</strong>
            <span>${entry.reason}</span>
            <span class="item-meta">${formatter.format(new Date(entry.created_at))} • Change: ${change}</span>
        `;
        container.appendChild(li);
    });
}

function renderUsage(entries) {
    const container = document.getElementById('usage-feed');
    container.innerHTML = '';
    const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    entries.forEach((entry) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <strong>${entry.client_name}</strong>
            <span>${entry.details}</span>
            <span class="item-meta">${formatter.format(new Date(entry.created_at))} • Total ${formatCurrency(entry.total_cost)}</span>
        `;
        container.appendChild(li);
    });
}

function drawBarChart(canvas, labels, values, options = {}) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.clientWidth;
    const height = canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, width, height);
    if (!labels.length) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '16px Inter';
        ctx.fillText('No data available', 16, height / 2);
        return;
    }
    const padding = 32;
    const chartHeight = height - padding * 2;
    const barWidth = Math.max((width - padding * 2) / (labels.length * 1.5), 32);
    const maxValue = Math.max(...values, 1);
    ctx.font = '14px Inter';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#6b7280';
    labels.forEach((label, index) => {
        const x = padding + index * (barWidth * 1.5) + barWidth / 2;
        const barHeight = (values[index] / maxValue) * chartHeight;
        const y = height - padding - barHeight;
        const gradient = ctx.createLinearGradient(x - barWidth / 2, y, x + barWidth / 2, height - padding);
        gradient.addColorStop(0, options.colorStart || '#4b7bec');
        gradient.addColorStop(1, options.colorEnd || '#3dc1d3');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x - barWidth / 2, y, barWidth, barHeight, 8);
        ctx.fill();
        ctx.fillStyle = '#1f2937';
        ctx.fillText(values[index], x, y - 8);
        ctx.save();
        ctx.fillStyle = '#6b7280';
        ctx.translate(x, height - padding + 14);
        ctx.rotate(-Math.PI / 4);
        ctx.fillText(label, 0, 0);
        ctx.restore();
    });
}

function drawDonutChart(canvas, segments) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.clientWidth;
    const height = canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, width, height);
    const total = segments.reduce((sum, seg) => sum + seg.value, 0);
    if (total === 0) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '16px Inter';
        ctx.fillText('No data available', width / 2 - 60, height / 2);
        return;
    }
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 20;
    let startAngle = -Math.PI / 2;
    segments.forEach((segment) => {
        const endAngle = startAngle + (segment.value / total) * Math.PI * 2;
        const gradient = ctx.createLinearGradient(centerX, centerY - radius, centerX, centerY + radius);
        gradient.addColorStop(0, segment.colorStart);
        gradient.addColorStop(1, segment.colorEnd);
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
        startAngle = endAngle;
    });
    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.55, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#111827';
    ctx.font = '16px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Stock Health', centerX, centerY + 6);
}

async function loadDashboard() {
    const data = await request('/api/dashboard');
    state.items = data.items;
    document.getElementById('metric-value').textContent = formatCurrency(data.total_value);
    document.getElementById('metric-units').textContent = data.total_units;
    document.querySelector('#metric-low-stock .metric').textContent = data.low_stock.length;
    document.querySelector('#metric-overstock .metric').textContent = data.overstock.length;
    renderInventory(data.items);
    renderActivity(data.movements);
    renderUsage(data.recent_usage);
    drawBarChart(
        document.getElementById('stock-distribution'),
        data.items.map((item) => item.name),
        data.items.map((item) => item.stock_level),
        { colorStart: '#4b7bec', colorEnd: '#a855f7' }
    );
    drawDonutChart(
        document.getElementById('stock-health'),
        [
            { value: data.low_stock.length, colorStart: '#f97316', colorEnd: '#facc15' },
            { value: data.overstock.length, colorStart: '#22d3ee', colorEnd: '#3b82f6' },
            { value: data.items.length - data.low_stock.length - data.overstock.length, colorStart: '#34d399', colorEnd: '#10b981' },
        ]
    );
}

async function loadShoppingList() {
    const data = await request('/api/shopping-list');
    state.shoppingList = data.items;
    renderShoppingList(data.items);
}

async function refreshAll() {
    await Promise.all([loadDashboard(), loadShoppingList()]);
}

function buildUsageRow(index) {
    const row = document.createElement('div');
    row.className = 'usage-item-row';
    row.innerHTML = `
        <div class="input-group">
            <label for="usage-barcode-${index}">Barcode / ID</label>
            <input id="usage-barcode-${index}" name="barcode" required>
        </div>
        <div class="input-group">
            <label for="usage-amount-${index}">Amount Used</label>
            <input id="usage-amount-${index}" name="amount" type="number" min="1" required>
        </div>
        <div class="input-group">
            <label for="usage-preview-${index}">Preview Cost</label>
            <input id="usage-preview-${index}" name="preview" readonly>
        </div>
        <div class="input-group">
            <label>&nbsp;</label>
            <button type="button" class="tertiary remove-usage">Remove</button>
        </div>
    `;
    return row;
}

function updateUsagePreview(container) {
    const rows = container.querySelectorAll('.usage-item-row');
    let total = 0;
    rows.forEach((row) => {
        const barcode = row.querySelector('input[name="barcode"]').value.trim();
        const amount = Number(row.querySelector('input[name="amount"]').value);
        const preview = row.querySelector('input[name="preview"]');
        const item = state.items.find((itm) => itm.barcode === barcode);
        if (item && amount > 0) {
            const cost = amount * item.unit_cost;
            preview.value = formatCurrency(cost);
            total += cost;
        } else {
            preview.value = '';
        }
    });
    document.getElementById('usage-total-cost').textContent = formatCurrency(total);
}

function setupForms() {
    const addForm = document.getElementById('add-item-form');
    addForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(addForm);
        const payload = Object.fromEntries(formData.entries());
        payload.attributes = parseAttributes(payload.attributes || '');
        try {
            await request('/api/items', { method: 'POST', body: JSON.stringify(payload) });
            addForm.reset();
            showToast('Item added successfully', 'success');
            await refreshAll();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    const adjustForm = document.getElementById('adjust-form');
    adjustForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(adjustForm);
        const payload = Object.fromEntries(formData.entries());
        payload.delta = Number(payload.delta);
        try {
            await request('/api/items/adjust', { method: 'POST', body: JSON.stringify(payload) });
            adjustForm.reset();
            showToast('Stock updated', 'success');
            await refreshAll();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });

    const usageForm = document.getElementById('usage-form');
    const usageContainer = document.getElementById('usage-items-container');

    function addUsageRow() {
        const index = usageContainer.children.length;
        const row = buildUsageRow(index);
        usageContainer.appendChild(row);
        updateUsagePreview(usageContainer);
        row.querySelectorAll('input').forEach((input) => {
            input.addEventListener('input', () => updateUsagePreview(usageContainer));
        });
        row.querySelector('.remove-usage').addEventListener('click', () => {
            row.remove();
            updateUsagePreview(usageContainer);
        });
    }

    document.getElementById('add-usage-item').addEventListener('click', () => {
        addUsageRow();
    });

    addUsageRow();

    usageForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(usageForm);
        const payload = {
            client_name: formData.get('client_name'),
            usage_date: formData.get('usage_date'),
            before_state: formData.get('before_state'),
            after_state: formData.get('after_state'),
            items: [],
        };
        usageContainer.querySelectorAll('.usage-item-row').forEach((row) => {
            const barcode = row.querySelector('input[name="barcode"]').value.trim();
            const amount = Number(row.querySelector('input[name="amount"]').value);
            if (barcode && amount > 0) {
                payload.items.push({ barcode, amount });
            }
        });
        try {
            const result = await request('/api/usage', { method: 'POST', body: JSON.stringify(payload) });
            showToast(`Usage recorded. Total ${formatCurrency(result.total_cost)}`, 'success');
            usageForm.reset();
            usageContainer.innerHTML = '';
            addUsageRow();
            await refreshAll();
        } catch (error) {
            showToast(error.message, 'error');
        }
    });
}

function setupNavigation() {
    document.querySelectorAll('.nav-link').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const target = document.querySelector(link.getAttribute('href'));
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
}

async function init() {
    setupForms();
    setupNavigation();
    await refreshAll();
    setInterval(refreshAll, 60_000);
}

document.addEventListener('DOMContentLoaded', init);
