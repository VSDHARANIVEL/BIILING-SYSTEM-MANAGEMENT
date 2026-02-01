from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3, json, datetime

app = Flask(__name__)
CORS(app)

# Initialize Database with 132 Workers
def init_db():
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    
    # Customers Table
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, last_bill_id INTEGER)''')
    
    # Stock Table (500 clothes capacity)
    c.execute('''CREATE TABLE IF NOT EXISTS stock 
                 (id INTEGER PRIMARY KEY, item_name TEXT, size TEXT, color TEXT, 
                  quantity INTEGER, price REAL, added_date TEXT)''')
    
    # Bills Table
    c.execute('''CREATE TABLE IF NOT EXISTS bills 
                 (id INTEGER PRIMARY KEY, customer_phone TEXT, bill_date TEXT, total REAL, 
                  items_json TEXT, worker_id INTEGER, pieces_sold INTEGER)''')
    
    # Workers Table (132 workers)
    c.execute('''CREATE TABLE IF NOT EXISTS workers 
                 (id INTEGER PRIMARY KEY, name TEXT, incentives REAL DEFAULT 0)''')
    
    # CREATE 132 WORKERS AUTOMATICALLY
    for i in range(1, 133):
        c.execute("INSERT OR IGNORE INTO workers (id, name, incentives) VALUES (?, ?, 0)", 
                  (i, f"Worker-{i}"))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with 132 workers!")

init_db()

# Get Current Stock
@app.route('/api/stock', methods=['GET'])
def get_stock():
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    c.execute("SELECT * FROM stock WHERE quantity > 0 ORDER BY item_name")
    stock = [{"id": r[0], "item": r[1], "size": r[2], "color": r[3], 
              "qty": r[4], "price": r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify(stock)

# Add Stock (for daily additions)
@app.route('/api/stock/add', methods=['POST'])
def add_stock():
    data = request.json
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    c.execute("INSERT INTO stock (item_name, size, color, quantity, price, added_date) VALUES (?, ?, ?, ?, ?, ?)",
              (data['item'], data['size'], data['color'], data['qty'], data['price'], 
               datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# Get Last Bill by Phone
@app.route('/api/customer/last-bill/<phone>')
def get_last_bill(phone):
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    c.execute("SELECT items_json, total FROM bills WHERE customer_phone=? ORDER BY id DESC LIMIT 1", (phone,))
    r = c.fetchone()
    conn.close()
    return jsonify({"items_json": r[0] if r else "[]", "total": r[1] if r else 0})

# Save Bill - Worker gets ₹1 per piece
@app.route('/api/bill/save', methods=['POST'])
def save_bill():
    data = request.json
    phone = data['customer_phone']
    worker_id = int(data['worker_id'])  # 1-132
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    
    # Customer
    c.execute("INSERT OR IGNORE INTO customers (phone, name) VALUES (?, ?)", 
              (phone, data['customer_name']))
    c.execute("UPDATE customers SET name=? WHERE phone=?", (data['customer_name'], phone))
    
    # Total pieces this bill
    total_pieces = sum(item['qty_billed'] for item in data['items'])
    
    # Deduct stock
    for item in data['items']:
        c.execute("UPDATE stock SET quantity = quantity - ? WHERE id=?", 
                  (item['qty_billed'], item['id']))
    
    # Save bill
    c.execute("INSERT INTO bills (customer_phone, bill_date, total, items_json, worker_id, pieces_sold) VALUES (?, ?, ?, ?, ?, ?)",
              (phone, today, data['total'], json.dumps(data['items']), worker_id, total_pieces))
    
    # WORKER INCENTIVE: ₹1 per piece
    c.execute("UPDATE workers SET incentives = incentives + ? WHERE id = ?", (total_pieces, worker_id))
    
    bill_id = c.lastrowid
    c.execute("UPDATE customers SET last_bill_id=? WHERE phone=?", (bill_id, phone))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "pieces": total_pieces, "worker": worker_id})

# Get Workers (Top 20 by incentive)
@app.route('/api/workers', methods=['GET'])
def get_workers():
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    c.execute("SELECT id, name, incentives FROM workers ORDER BY incentives DESC LIMIT 20")
    workers = [{"id": r[0], "name": r[1], "incentive": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(workers)

# Reset Monthly Incentives
@app.route('/api/incentives/reset', methods=['POST'])
def reset_incentives():
    conn = sqlite3.connect('billing.db')
    c = conn.cursor()
    c.execute("UPDATE workers SET incentives = 0")
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# Frontend
@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    app.run(debug=True, port=5000)
