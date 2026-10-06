from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json, os, sqlite3, datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
BASE = os.path.dirname(os.path.abspath(__file__))

# Use persistent volume on Railway, fallback to /tmp
DB = os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '/tmp'), 'leases.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS leases (
        id TEXT PRIMARY KEY, tenant TEXT, address TEXT, building TEXT,
        expiration TEXT, exp_sort TEXT, source TEXT, notes TEXT, updated_at TEXT
    )''')
    conn.commit()
    if conn.execute('SELECT COUNT(*) FROM leases').fetchone()[0] == 0:
        seed_path = os.path.join(BASE, 'seed.json')
        if os.path.exists(seed_path):
            with open(seed_path, encoding='utf-8') as f:
                seed = json.load(f)
            now = datetime.datetime.utcnow().isoformat()
            for l in seed:
                conn.execute(
                    'INSERT OR IGNORE INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
                    (l.get('id',''), l.get('tenant',''), l.get('address',''), l.get('building',''),
                     l.get('expiration',''), l.get('exp_sort',''), l.get('source',''), l.get('notes',''), now))
            conn.commit()
    conn.close()

init_db()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def index():
    with open(os.path.join(BASE, 'static', 'index.html'), encoding='utf-8') as f:
        return Response(f.read(), mimetype='text/html')

@app.route('/api/leases', methods=['GET','OPTIONS'])
def get_leases():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    conn = get_db()
    rows = [dict(r) for r in conn.execute('SELECT * FROM leases ORDER BY exp_sort').fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/leases', methods=['POST'])
def add_lease():
    d = request.json
    conn = get_db()
    conn.execute(
        'INSERT OR REPLACE INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
        (d.get('id'), d.get('tenant'), d.get('address'), d.get('building'),
         d.get('expiration'), d.get('exp_sort'), d.get('source'), d.get('notes'),
         datetime.datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['PUT','OPTIONS'])
def update_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    d = request.json
    conn = get_db()
    conn.execute(
        'UPDATE leases SET tenant=?,address=?,building=?,expiration=?,exp_sort=?,source=?,notes=?,updated_at=? WHERE id=?',
        (d.get('tenant'), d.get('address'), d.get('building'), d.get('expiration'),
         d.get('exp_sort'), d.get('source'), d.get('notes'),
         datetime.datetime.utcnow().isoformat(), lid))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['DELETE','OPTIONS'])
def delete_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    conn = get_db()
    conn.execute('DELETE FROM leases WHERE id=?', (lid,))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
