import json
import os
import socket
import sqlite3
from urllib.parse import urlparse, urlunparse
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

# PostgreSQL support (optional, via env vars)
DATABASE_URL = os.environ.get('DATABASE_URL')
# Support individual env vars as alternative to DATABASE_URL
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'postgres')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
USE_POSTGRES = bool(DATABASE_URL or DB_HOST)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


def resolve_ipv4(hostname):
    """Resolve hostname to IPv4 address to avoid IPv6 connectivity issues."""
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if results:
            return results[0][4][0]
    except socket.gaierror:
        pass
    return hostname


def pg_connect(**kwargs):
    """Connect to PostgreSQL, always using individual params with IPv4 resolution."""
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        host = parsed.hostname
        port = parsed.port or 5432
        dbname = parsed.path.lstrip('/') or 'postgres'
        user = parsed.username or 'postgres'
        password = parsed.password
    else:
        host = DB_HOST
        port = int(DB_PORT)
        dbname = DB_NAME
        user = DB_USER
        password = DB_PASSWORD
    ip = resolve_ipv4(host)
    return psycopg2.connect(
        host=ip, port=port, dbname=dbname,
        user=user, password=password,
        sslmode='require', **kwargs
    )

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


def get_db():
    if 'db' not in g:
        if USE_POSTGRES:
            g.db = pg_connect(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


def db_execute(query, params=None):
    """Execute a query, translating ? placeholders to %s for PostgreSQL."""
    db = get_db()
    if USE_POSTGRES:
        query = query.replace('?', '%s')
        cur = db.cursor()
        cur.execute(query, params or ())
        return cur
    else:
        return db.execute(query, params or ())


def db_commit():
    get_db().commit()


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    if USE_POSTGRES:
        conn = pg_connect()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL DEFAULT 0
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            items TEXT,
            total DOUBLE PRECISION,
            session_id TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'new'
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            started_at TEXT,
            ended_at TEXT
        )''')
        cur.execute('SELECT COUNT(*) FROM products')
        count = cur.fetchone()[0]
        if count == 0:
            for p in DEFAULT_PRODUCTS:
                cur.execute(
                    'INSERT INTO products (id, name, category, price) VALUES (%s, %s, %s, %s)',
                    (p['id'], p['name'], p['category'], p['price'])
                )
            # Reset sequence to max id so future inserts get correct IDs
            cur.execute("SELECT setval('products_id_seq', (SELECT MAX(id) FROM products))")
        conn.commit()
        cur.close()
        conn.close()
    else:
        db = sqlite3.connect(DB_PATH)
        db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY,
            items TEXT,
            total REAL,
            session_id TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'new'
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            started_at TEXT,
            ended_at TEXT
        )''')
        count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if count == 0:
            for p in DEFAULT_PRODUCTS:
                db.execute('INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)',
                           (p['id'], p['name'], p['category'], p['price']))
        db.commit()
        db.close()

init_db()


def row_to_dict(row):
    return dict(row)


# ── Health ──

@app.route('/api/ping')
def ping():
    return jsonify({"status": "ok"})


# ── Products ──

@app.route('/api/products', methods=['GET'])
def get_products():
    rows = db_execute('SELECT * FROM products').fetchall()
    return jsonify([row_to_dict(r) for r in rows])


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
    if USE_POSTGRES:
        cur = db_execute('INSERT INTO products (name, category, price) VALUES (?, ?, ?) RETURNING id',
                         (name, category, price))
        new_id = cur.fetchone()['id']
    else:
        cur = db_execute('INSERT INTO products (name, category, price) VALUES (?, ?, ?)',
                         (name, category, price))
        new_id = cur.lastrowid
    db_commit()
    product = row_to_dict(db_execute('SELECT * FROM products WHERE id = ?', (new_id,)).fetchone())
    return jsonify(product), 201


@app.route('/api/products/reset', methods=['POST'])
def reset_products():
    db_execute('DELETE FROM products')
    for p in DEFAULT_PRODUCTS:
        db_execute('INSERT INTO products (id, name, category, price) VALUES (?, ?, ?, ?)',
                   (p['id'], p['name'], p['category'], p['price']))
    if USE_POSTGRES:
        db_execute("SELECT setval('products_id_seq', (SELECT MAX(id) FROM products))")
    db_commit()
    rows = db_execute('SELECT * FROM products').fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    existing = db_execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Product not found"}), 404
    existing = row_to_dict(existing)
    name = data.get('name', existing['name'])
    category = data.get('category', existing['category'])
    price = data.get('price', existing['price'])
    db_execute('UPDATE products SET name = ?, category = ?, price = ? WHERE id = ?',
               (name, category, price, product_id))
    db_commit()
    product = row_to_dict(db_execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone())
    return jsonify(product)


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    existing = db_execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Product not found"}), 404
    db_execute('DELETE FROM products WHERE id = ?', (product_id,))
    db_commit()
    return jsonify({"deleted": product_id})


# ── Tickets ──

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
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
    rows = db_execute(query, params).fetchall()
    tickets = []
    for r in rows:
        t = row_to_dict(r)
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
    items_json = json.dumps(items) if not isinstance(items, str) else items
    if USE_POSTGRES:
        cur = db_execute(
            'INSERT INTO tickets (items, total, session_id, created_at, status) VALUES (?, ?, ?, ?, ?) RETURNING id',
            (items_json, data.get('total', 0), data.get('session_id'), data.get('created_at'), data.get('status', 'new'))
        )
        new_id = cur.fetchone()['id']
    else:
        cur = db_execute(
            'INSERT INTO tickets (items, total, session_id, created_at, status) VALUES (?, ?, ?, ?, ?)',
            (items_json, data.get('total', 0), data.get('session_id'), data.get('created_at'), data.get('status', 'new'))
        )
        new_id = cur.lastrowid
    db_commit()
    ticket = row_to_dict(db_execute('SELECT * FROM tickets WHERE id = ?', (new_id,)).fetchone())
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
    existing = db_execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Ticket not found"}), 404
    existing = row_to_dict(existing)
    items = data.get('items', existing['items'])
    if isinstance(items, list):
        items = json.dumps(items)
    total = data.get('total', existing['total'])
    session_id = data.get('session_id', existing['session_id'])
    created_at = data.get('created_at', existing['created_at'])
    status = data.get('status', existing['status'])
    db_execute('UPDATE tickets SET items = ?, total = ?, session_id = ?, created_at = ?, status = ? WHERE id = ?',
               (items, total, session_id, created_at, status, ticket_id))
    db_commit()
    ticket = row_to_dict(db_execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone())
    try:
        ticket['items'] = json.loads(ticket['items']) if ticket['items'] else []
    except (json.JSONDecodeError, TypeError):
        ticket['items'] = []
    return jsonify(ticket)


@app.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    existing = db_execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Ticket not found"}), 404
    db_execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    db_commit()
    return jsonify({"deleted": ticket_id})


@app.route('/api/tickets/import', methods=['POST'])
def import_tickets():
    """Import tickets from a JSON array (e.g. exported localStorage data)."""
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of tickets"}), 400
    imported = 0
    for ticket in data:
        items = ticket.get('items', [])
        items_json = json.dumps(items) if isinstance(items, list) else items
        total = ticket.get('total', 0)
        session_id = ticket.get('session_id')
        if session_id is not None:
            session_id = str(session_id)
        created_at = ticket.get('created_at')
        status = ticket.get('status', 'done')
        db_execute(
            'INSERT INTO tickets (items, total, session_id, created_at, status) VALUES (?, ?, ?, ?, ?)',
            (items_json, total, session_id, created_at, status)
        )
        imported += 1
    db_commit()
    return jsonify({"imported": imported}), 201


# ── Sessions ──

@app.route('/api/sessions/current', methods=['GET'])
def get_current_session():
    row = db_execute('SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        return jsonify(None)
    return jsonify(row_to_dict(row))


@app.route('/api/sessions', methods=['POST'])
def create_session():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if USE_POSTGRES:
        cur = db_execute('INSERT INTO sessions (started_at, ended_at) VALUES (?, ?) RETURNING id',
                         (data.get('started_at'), data.get('ended_at')))
        new_id = cur.fetchone()['id']
    else:
        cur = db_execute('INSERT INTO sessions (started_at, ended_at) VALUES (?, ?)',
                         (data.get('started_at'), data.get('ended_at')))
        new_id = cur.lastrowid
    db_commit()
    session = row_to_dict(db_execute('SELECT * FROM sessions WHERE id = ?', (new_id,)).fetchone())
    return jsonify(session), 201


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    existing = db_execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Session not found"}), 404
    existing = row_to_dict(existing)
    started_at = data.get('started_at', existing['started_at'])
    ended_at = data.get('ended_at', existing['ended_at'])
    db_execute('UPDATE sessions SET started_at = ?, ended_at = ? WHERE id = ?',
               (started_at, ended_at, session_id))
    db_commit()
    session = row_to_dict(db_execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone())
    return jsonify(session)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=True)
