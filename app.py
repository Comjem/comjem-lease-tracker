bash

cat /home/claude/comjem_app/app.py
Output

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json, os, sqlite3, datetime

app = Flask(__name__)
CORS(app)

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leases.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS leases (
        id TEXT PRIMARY KEY,
        tenant TEXT,
        address TEXT,
        building TEXT,
        expiration TEXT,
        exp_sort TEXT,
        source TEXT,
        notes TEXT,
        updated_at TEXT
    )''')
    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM leases').fetchone()[0]
    if count == 0:
        seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed.json')
        if os.path.exists(seed_file):
            with open(seed_file) as f:
                leases = json.load(f)
            for l in leases:
                conn.execute('''INSERT OR IGNORE INTO leases
                    (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)''',
                    (l.get('id',''), l.get('tenant',''), l.get('address',''),
                     l.get('building',''), l.get('expiration',''), l.get('exp_sort',''),
                     l.get('source',''), l.get('notes',''),
                     datetime.datetime.utcnow().isoformat()))
            conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')
    if os.path.exists(html_path):
        with open(html_path, encoding='utf-8') as f:
            return Response(f.read(), mimetype='text/html')
    return Response('<h2>App is running. Static files not found.</h2>', mimetype='text/html')

@app.route('/api/leases', methods=['GET'])
def get_leases():
    conn = get_db()
    rows = conn.execute('SELECT * FROM leases ORDER BY exp_sort').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/leases', methods=['POST'])
def add_lease():
    data = request.json
    conn = get_db()
    conn.execute('''INSERT OR REPLACE INTO leases
        (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)''',
        (data.get('id'), data.get('tenant'), data.get('address'),
         data.get('building'), data.get('expiration'), data.get('exp_sort'),
         data.get('source'), data.get('notes'),
         datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['PUT'])
def update_lease(lid):
    data = request.json
    conn = get_db()
    conn.execute('''UPDATE leases SET tenant=?,address=?,building=?,
        expiration=?,exp_sort=?,source=?,notes=?,updated_at=? WHERE id=?''',
        (data.get('tenant'), data.get('address'), data.get('building'),
         data.get('expiration'), data.get('exp_sort'), data.get('source'),
         data.get('notes'), datetime.datetime.utcnow().isoformat(), lid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['DELETE'])
def delete_lease(lid):
    conn = get_db()
    conn.execute('DELETE FROM leases WHERE id=?', (lid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
