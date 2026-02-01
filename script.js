let stock = [];
let billItems = [];
let lastBill = { items_json: "[]", total: 0 };
let workers = [];

// Load everything on start
async function init() {
    await loadStock();
    await loadWorkers();
    workerNumber.addEventListener('input', showWorkerInfo);
}

async function loadStock() {
    const res = await fetch('/api/stock');
    stock = await res.json();
    renderStock();
}

function renderStock() {
    document.getElementById('stockList').innerHTML = stock.map(s => `
        <div class="stock-item">
            ${s.item} (${s.size}/${s.color}) | ${s.qty} pcs @ ₹${s.price}
            <button onclick="addToBill(${s.id})" style="float:right;">➕ Add to Bill</button>
        </div>
    `).join('') || '<div>No stock available. Add stock first!</div>';
}

async function fetchLastBill() {
    const phone = document.getElementById('phone').value;
    if (phone.length > 5) {
        const res = await fetch(`/api/customer/last-bill/${phone}`);
        lastBill = await res.json();
        document.getElementById('lastBill').innerHTML = 
            `Last Bill: ₹${lastBill.total} | Items: ${JSON.parse(lastBill.items_json || '[]').length}`;
    }
}

function addToBill(stockId) {
    const item = stock.find(s => s.id == stockId);
    billItems.push({ ...item, qty_billed: 1 });
    renderBill();
}

function renderBill() {
    document.getElementById('billItems').innerHTML = billItems.map((item, i) => `
        <div class="bill-item">
            ${item.item} (${item.size}) x 
            <input type="number" value="${item.qty_billed}" min="1" style="width:60px;" 
                   onchange="updateQty(${i}, this.value)">
            = ₹${(item.qty_billed * item.price).toFixed(2)}
            <button onclick="removeItem(${i})" style="background:#f44336;">❌</button>
        </div>
    `).join('') || '<div>No items in bill. Add from stock above.</div>';
}

function updateQty(index, qty) {
    billItems[index].qty_billed = parseInt(qty);
    renderBill();
}

function removeItem(index) {
    billItems.splice(index, 1);
    renderBill();
}

async function generateBill() {
    if (billItems.length === 0) return alert('Add items to bill first!');
    
    const worker_id = parseInt(document.getElementById('workerNumber').value);
    if (!worker_id || worker_id < 1 || worker_id > 132) {
        return alert('Enter valid Worker Number (1-132)');
    }
    
    const total = billItems.reduce((sum, i) => sum + (i.qty_billed * i.price), 0);
    
    const data = {
        customer_name: document.getElementById('customerName').value || 'Cash Customer',
        customer_phone: document.getElementById('phone').value,
        items: billItems,
        total,
        worker_id
    };
    
    const res = await fetch('/api/bill/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    const result = await res.json();
    alert(`✅ Bill Saved!\nTotal: ₹${total}\nPieces: ${result.pieces}\nWorker-${worker_id} gets ₹${result.pieces}`);
    
    billItems = [];
    document.getElementById('workerNumber').value = '';
    document.getElementById('phone').value = '';
    await loadStock();
}

function showWorkerInfo() {
    const num = document.getElementById('workerNumber').value;
    document.getElementById('workerInfo').innerHTML = 
        num && num >= 1 && num <= 132 ? `Worker-${num}` : '';
}

async function showAddStock() {
    const item = prompt('Item Name (ex: Shirt):');
    const size = prompt('Size (S/M/L/XL):');
    const color = prompt('Color:');
    const qty = parseInt(prompt('Quantity:')) || 0;
    const price = parseFloat(prompt('Price per piece:')) || 0;
    
    if (item && qty > 0) {
        await fetch('/api/stock/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item, size, color, qty, price })
        });
        loadStock();
    }
}

async function loadWorkers() {
    const res = await fetch('/api/workers');
    workers = await res.json();
}

async function loadIncentives() {
    await loadWorkers();
    document.getElementById('incentivesList').innerHTML = workers.map(w => `
        <div><strong>Worker-${w.id}:</strong> ₹${w.incentive.toFixed(0)} 
            (${w.incentive.toFixed(0)} pieces)</div>
    `).join('');
}

async function resetMonth() {
    if (confirm('Reset all worker incentives?')) {
        await fetch('/api/incentives/reset', { method: 'POST' });
        loadIncentives();
    }
}

// START APP
init();
