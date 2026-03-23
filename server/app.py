import json
import os
import sqlite3
import requests
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

# Supabase REST API support (optional, via env vars)
SUPABASE_URL = os.environ.get('SUPABASE_URL')  # e.g. https://xxx.supabase.co
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')  # service_role key
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')

app = Flask(__name__)
CORS(app, resources={r'/api/*': {'origins': '*'}})


@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')

DEFAULT_PRODUCTS = [
    {"id": 400, "name": "Sahfa Dro3", "category": "COIN DRO3", "price": 2.0},
    {"id": 401, "name": "Sahfa Yawmiya", "category": "COIN DRO3", "price": 3.0},
    {"id": 402, "name": "Sahfa Mshakhshkha", "category": "COIN DRO3", "price": 6.0},
    {"id": 403, "name": "Sahfa Mahmula", "category": "COIN DRO3", "price": 0.8},
    {"id": 404, "name": "Thon", "category": "COIN MELAH", "price": 3.9},
    {"id": 405, "name": "Salami", "category": "COIN MELAH", "price": 2.5},
    {"id": 406, "name": "Jambon", "category": "COIN MELAH", "price": 2.7},
    {"id": 407, "name": "Salami Hsan", "category": "COIN MELAH", "price": 4.0},
    {"id": 408, "name": "Supp Thon", "category": "COIN MELAH", "price": 2.5},
    {"id": 409, "name": "Supp Salami", "category": "COIN MELAH", "price": 1.5},
    {"id": 410, "name": "Supp Jambon", "category": "COIN MELAH", "price": 1.5},
    {"id": 411, "name": "Supp Salami Hsan", "category": "COIN MELAH", "price": 3.0},
    {"id": 412, "name": "Supp Ricotta", "category": "COIN MELAH", "price": 1.0},
    {"id": 413, "name": "Supp Gruyere", "category": "COIN MELAH", "price": 2.5},
    {"id": 414, "name": "Supp Fromage Triangle", "category": "COIN MELAH", "price": 0.6},
    {"id": 423, "name": "Supp Adma", "category": "COIN MELAH", "price": 0.5},
    {"id": 415, "name": "Khobz Mlawi", "category": "COIN HLOU", "price": 0.6},
    {"id": 416, "name": "Khobz Tabuna", "category": "COIN HLOU", "price": 0.6},
    {"id": 417, "name": "Zbeda/Ma3jun/Shamiya", "category": "COIN HLOU", "price": 1.8},
    {"id": 418, "name": "Zbeda + Ma3jun/Shamiya", "category": "COIN HLOU", "price": 2.1},
    {"id": 419, "name": "Ma3jun + Shamiya", "category": "COIN HLOU", "price": 2.1},
    {"id": 420, "name": "Zbeda + Ma3jun + Shamiya", "category": "COIN HLOU", "price": 2.4},
    {"id": 421, "name": "Ricotta", "category": "COIN HLOU", "price": 2.1},
    {"id": 422, "name": "Ricotta + Zbeda/Ma3jun/Shamiya", "category": "COIN HLOU", "price": 2.4},
    {"id": 424, "name": "Ricotta + Zbeda + Ma3jun/Shamiya", "category": "COIN HLOU", "price": 2.7},
    {"id": 425, "name": "Ricotta + Ma3jun + Shamiya", "category": "COIN HLOU", "price": 2.7},
    {"id": 426, "name": "Ricotta + Zbeda + Ma3jun + Shamiya", "category": "COIN HLOU", "price": 3.0},
    {"id": 427, "name": "Douza Chocolat", "category": "COIN HLOU", "price": 0.8},
    {"id": 428, "name": "Douza Asal", "category": "COIN HLOU", "price": 0.5},
    {"id": 429, "name": "Zbeda Arbi", "category": "COIN HLOU", "price": 0.5},
]


# ── Supabase REST helpers ──

def sb_headers(prefer=None):
    h = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}', 'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    return h


def sb_get(table, params=None):
    r = requests.get(f'{SUPABASE_URL}/rest/v1/{table}', headers=sb_headers(), params=params or {}, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_post(table, data, return_row=True):
    prefer = 'return=representation' if return_row else 'return=minimal'
    r = requests.post(f'{SUPABASE_URL}/rest/v1/{table}', headers=sb_headers(prefer), json=data, timeout=10)
    r.raise_for_status()
    return r.json() if return_row else None


def sb_patch(table, match, data):
    r = requests.patch(f'{SUPABASE_URL}/rest/v1/{table}', headers=sb_headers('return=representation'),
                       params=match, json=data, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_delete(table, match):
    r = requests.delete(f'{SUPABASE_URL}/rest/v1/{table}', headers=sb_headers(), params=match, timeout=10)
    r.raise_for_status()


# ── SQLite fallback helpers ──

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    global USE_SUPABASE
    if USE_SUPABASE:
        try:
            # Test connection and seed products if empty
            products = sb_get('products', {'select': 'id', 'limit': '1'})
            if len(products) == 0:
                sb_post('products', DEFAULT_PRODUCTS, return_row=False)
            print(f"[INFO] Connected to Supabase: {SUPABASE_URL}")
        except Exception as e:
            print(f"[WARN] Supabase connection failed: {e}")
            print("[WARN] Falling back to SQLite")
            USE_SUPABASE = False
            init_db()
            return
    else:
        db = sqlite3.connect(DB_PATH)
        db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            category TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)''')
        db.execute('''CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY, items TEXT, total REAL,
            session_id TEXT, created_at TEXT, status TEXT DEFAULT 'new')''')
        db.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY, started_at TEXT, ended_at TEXT)''')
        count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if count == 0:
            for p in DEFAULT_PRODUCTS:
                db.execute('INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)',
                           (p['id'], p['name'], p['category'], p['price']))
        db.commit()
        db.close()

init_db()


# ── Health ──

@app.route('/api/ping')
def ping():
    return jsonify({
        "status": "ok",
        "database": "supabase" if USE_SUPABASE else "sqlite",
    })


# ── Products ──

@app.route('/api/products', methods=['GET'])
def get_products():
    if USE_SUPABASE:
        return jsonify(sb_get('products'))
    db = get_db()
    rows = db.execute('SELECT * FROM products').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    name = data.get('name', '').strip()
    category = data.get('category', '').strip()
    price = data.get('price', 0)
    if not name or not category:
        return jsonify({"error": "Name and category are required"}), 400
    if USE_SUPABASE:
        rows = sb_post('products', {"name": name, "category": category, "price": price})
        return jsonify(rows[0] if rows else {}), 201
    db = get_db()
    cur = db.execute('INSERT INTO products (name, category, price) VALUES (?, ?, ?)', (name, category, price))
    db.commit()
    product = dict(db.execute('SELECT * FROM products WHERE id = ?', (cur.lastrowid,)).fetchone())
    return jsonify(product), 201


@app.route('/api/products/reset', methods=['POST'])
def reset_products():
    if USE_SUPABASE:
        sb_delete('products', {'id': 'gt.0'})
        sb_post('products', DEFAULT_PRODUCTS, return_row=False)
        return jsonify(sb_get('products'))
    db = get_db()
    db.execute('DELETE FROM products')
    for p in DEFAULT_PRODUCTS:
        db.execute('INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)',
                   (p['id'], p['name'], p['category'], p['price']))
    db.commit()
    rows = db.execute('SELECT * FROM products').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if USE_SUPABASE:
        existing = sb_get('products', {'id': f'eq.{product_id}'})
        if not existing:
            return jsonify({"error": "Product not found"}), 404
        update = {}
        if 'name' in data: update['name'] = data['name']
        if 'category' in data: update['category'] = data['category']
        if 'price' in data: update['price'] = data['price']
        rows = sb_patch('products', {'id': f'eq.{product_id}'}, update)
        return jsonify(rows[0] if rows else {})
    db = get_db()
    existing = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Product not found"}), 404
    existing = dict(existing)
    name = data.get('name', existing['name'])
    category = data.get('category', existing['category'])
    price = data.get('price', existing['price'])
    db.execute('UPDATE products SET name = ?, category = ?, price = ? WHERE id = ?',
               (name, category, price, product_id))
    db.commit()
    product = dict(db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone())
    return jsonify(product)


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if USE_SUPABASE:
        existing = sb_get('products', {'id': f'eq.{product_id}'})
        if not existing:
            return jsonify({"error": "Product not found"}), 404
        sb_delete('products', {'id': f'eq.{product_id}'})
        return jsonify({"deleted": product_id})
    db = get_db()
    existing = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Product not found"}), 404
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    return jsonify({"deleted": product_id})


# ── Tickets ──

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    if USE_SUPABASE:
        params = {}
        status_filter = request.args.get('status')
        if status_filter:
            statuses = [s.strip() for s in status_filter.split(',')]
            params['status'] = f'in.({",".join(statuses)})'
        session_id = request.args.get('session_id')
        if session_id:
            params['session_id'] = f'eq.{session_id}'
        tickets = sb_get('tickets', params)
        for t in tickets:
            if isinstance(t.get('items'), str):
                try:
                    t['items'] = json.loads(t['items'])
                except (json.JSONDecodeError, TypeError):
                    t['items'] = []
        return jsonify(tickets)
    db = get_db()
    query = 'SELECT * FROM tickets WHERE 1=1'
    params = []
    status_filter = request.args.get('status')
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',')]
        placeholders = ','.join('?' for _ in statuses)
        query += f' AND status IN ({placeholders})'
        params.extend(statuses)
    session_id = request.args.get('session_id')
    if session_id:
        query += ' AND session_id = ?'
        params.append(session_id)
    rows = db.execute(query, params).fetchall()
    tickets = []
    for r in rows:
        t = dict(r)
        try:
            t['items'] = json.loads(t['items']) if t['items'] else []
        except (json.JSONDecodeError, TypeError):
            t['items'] = []
        tickets.append(t)
    return jsonify(tickets)


@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    items = data.get('items', [])
    items_json = json.dumps(items) if isinstance(items, list) else items
    row = {
        "items": items_json, "total": data.get('total', 0),
        "session_id": str(data['session_id']) if data.get('session_id') is not None else None,
        "created_at": data.get('created_at'), "status": data.get('status', 'new')
    }
    if USE_SUPABASE:
        rows = sb_post('tickets', row)
        t = rows[0] if rows else {}
        if isinstance(t.get('items'), str):
            try:
                t['items'] = json.loads(t['items'])
            except (json.JSONDecodeError, TypeError):
                t['items'] = []
        return jsonify(t), 201
    db = get_db()
    cur = db.execute('INSERT INTO tickets (items, total, session_id, created_at, status) VALUES (?, ?, ?, ?, ?)',
                     (row['items'], row['total'], row['session_id'], row['created_at'], row['status']))
    db.commit()
    ticket = dict(db.execute('SELECT * FROM tickets WHERE id = ?', (cur.lastrowid,)).fetchone())
    try:
        ticket['items'] = json.loads(ticket['items']) if ticket['items'] else []
    except (json.JSONDecodeError, TypeError):
        ticket['items'] = []
    return jsonify(ticket), 201


@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if USE_SUPABASE:
        existing = sb_get('tickets', {'id': f'eq.{ticket_id}'})
        if not existing:
            return jsonify({"error": "Ticket not found"}), 404
        update = {}
        if 'items' in data:
            update['items'] = json.dumps(data['items']) if isinstance(data['items'], list) else data['items']
        if 'total' in data: update['total'] = data['total']
        if 'session_id' in data: update['session_id'] = str(data['session_id'])
        if 'created_at' in data: update['created_at'] = data['created_at']
        if 'status' in data: update['status'] = data['status']
        rows = sb_patch('tickets', {'id': f'eq.{ticket_id}'}, update)
        t = rows[0] if rows else {}
        if isinstance(t.get('items'), str):
            try:
                t['items'] = json.loads(t['items'])
            except (json.JSONDecodeError, TypeError):
                t['items'] = []
        return jsonify(t)
    db = get_db()
    existing = db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Ticket not found"}), 404
    existing = dict(existing)
    items = data.get('items', existing['items'])
    if isinstance(items, list):
        items = json.dumps(items)
    total = data.get('total', existing['total'])
    session_id = data.get('session_id', existing['session_id'])
    created_at = data.get('created_at', existing['created_at'])
    status = data.get('status', existing['status'])
    db.execute('UPDATE tickets SET items = ?, total = ?, session_id = ?, created_at = ?, status = ? WHERE id = ?',
               (items, total, session_id, created_at, status, ticket_id))
    db.commit()
    ticket = dict(db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone())
    try:
        ticket['items'] = json.loads(ticket['items']) if ticket['items'] else []
    except (json.JSONDecodeError, TypeError):
        ticket['items'] = []
    return jsonify(ticket)


@app.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    if USE_SUPABASE:
        existing = sb_get('tickets', {'id': f'eq.{ticket_id}'})
        if not existing:
            return jsonify({"error": "Ticket not found"}), 404
        sb_delete('tickets', {'id': f'eq.{ticket_id}'})
        return jsonify({"deleted": ticket_id})
    db = get_db()
    existing = db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Ticket not found"}), 404
    db.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    db.commit()
    return jsonify({"deleted": ticket_id})


@app.route('/api/tickets/import', methods=['POST'])
def import_tickets():
    """Import tickets from a JSON array, skipping duplicates."""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of tickets"}), 400

    # Load existing tickets to detect duplicates (by session_id + created_at + total)
    existing_keys = set()
    if USE_SUPABASE:
        existing = sb_get('tickets', {'select': 'session_id,created_at,total'})
    else:
        db = get_db()
        existing = [dict(r) for r in db.execute('SELECT session_id, created_at, total FROM tickets').fetchall()]
    for t in existing:
        key = f"{t.get('session_id')}|{t.get('created_at')}|{t.get('total')}"
        existing_keys.add(key)

    imported = 0
    skipped = 0
    for ticket in data:
        items = ticket.get('items', [])
        items_json = json.dumps(items) if isinstance(items, list) else items
        total = ticket.get('total', 0)
        session_id = ticket.get('session_id')
        if session_id is not None:
            session_id = str(session_id)
        created_at = ticket.get('created_at')
        status = ticket.get('status', 'done')

        # Check for duplicate
        key = f"{session_id}|{created_at}|{total}"
        if key in existing_keys:
            skipped += 1
            continue

        existing_keys.add(key)
        row = {"items": items_json, "total": total, "session_id": session_id,
               "created_at": created_at, "status": status}
        if USE_SUPABASE:
            sb_post('tickets', row, return_row=False)
        else:
            db = get_db()
            db.execute('INSERT INTO tickets (items, total, session_id, created_at, status) VALUES (?, ?, ?, ?, ?)',
                       (items_json, total, session_id, created_at, status))
        imported += 1
    if not USE_SUPABASE and imported > 0:
        get_db().commit()
    return jsonify({"imported": imported, "skipped": skipped, "total": len(data)}), 201


@app.route('/api/tickets/clear', methods=['POST'])
def clear_tickets():
    """Delete all tickets from the database."""
    if USE_SUPABASE:
        sb_delete('tickets', {'id': 'gt.0'})
    else:
        db = get_db()
        db.execute('DELETE FROM tickets')
        db.commit()
    return jsonify({"cleared": True})


@app.route('/api/sessions/clear', methods=['POST'])
def clear_sessions():
    """Delete all sessions from the database."""
    if USE_SUPABASE:
        sb_delete('sessions', {'id': 'gt.0'})
    else:
        db = get_db()
        db.execute('DELETE FROM sessions')
        db.commit()
    return jsonify({"cleared": True})


# ── Sessions ──

@app.route('/api/sessions/current', methods=['GET'])
def get_current_session():
    if USE_SUPABASE:
        rows = sb_get('sessions', {'ended_at': 'is.null', 'order': 'id.desc', 'limit': '1'})
        return jsonify(rows[0] if rows else None)
    db = get_db()
    row = db.execute('SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return jsonify(None)
    return jsonify(dict(row))


@app.route('/api/sessions', methods=['POST'])
def create_session():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if USE_SUPABASE:
        rows = sb_post('sessions', {"started_at": data.get('started_at'), "ended_at": data.get('ended_at')})
        return jsonify(rows[0] if rows else {}), 201
    db = get_db()
    cur = db.execute('INSERT INTO sessions (started_at, ended_at) VALUES (?, ?)',
                     (data.get('started_at'), data.get('ended_at')))
    db.commit()
    session = dict(db.execute('SELECT * FROM sessions WHERE id = ?', (cur.lastrowid,)).fetchone())
    return jsonify(session), 201


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if USE_SUPABASE:
        existing = sb_get('sessions', {'id': f'eq.{session_id}'})
        if not existing:
            return jsonify({"error": "Session not found"}), 404
        update = {}
        if 'started_at' in data: update['started_at'] = data['started_at']
        if 'ended_at' in data: update['ended_at'] = data['ended_at']
        rows = sb_patch('sessions', {'id': f'eq.{session_id}'}, update)
        return jsonify(rows[0] if rows else {})
    db = get_db()
    existing = db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Session not found"}), 404
    existing = dict(existing)
    started_at = data.get('started_at', existing['started_at'])
    ended_at = data.get('ended_at', existing['ended_at'])
    db.execute('UPDATE sessions SET started_at = ?, ended_at = ? WHERE id = ?',
               (started_at, ended_at, session_id))
    db.commit()
    session = dict(db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone())
    return jsonify(session)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=True)
