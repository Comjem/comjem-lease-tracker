from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json, os, datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
BASE = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:C5+7Z7kTVqsbWSh@db.eazplxtbrsmhnluinqta.supabase.co:5432/postgres')

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, sslmode='require')

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS leases (
        id TEXT PRIMARY KEY, tenant TEXT, address TEXT, building TEXT,
        expiration TEXT, exp_sort TEXT, source TEXT, notes TEXT, updated_at TEXT
    )''')
    conn.commit()
    cur.execute('SELECT COUNT(*) as cnt FROM leases')
    count = cur.fetchone()['cnt']
    if count == 0:
        seed_path = os.path.join(BASE, 'seed.json')
        if os.path.exists(seed_path):
            with open(seed_path, encoding='utf-8') as f:
                seed = json.load(f)
            now = datetime.datetime.utcnow().isoformat()
            for l in seed:
                cur.execute(
                    'INSERT INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING',
                    (l.get('id',''), l.get('tenant',''), l.get('address',''), l.get('building',''),
                     l.get('expiration',''), l.get('exp_sort',''), l.get('source',''), l.get('notes',''), now))
            conn.commit()
    cur.close(); conn.close()

try:
    init_db()
except Exception as e:
    print('DB init error:', e)

COLS = ['id','tenant','address','building','expiration','exp_sort','source','notes','updated_at']

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
    conn = get_db(); cur = conn.cursor()
    cur.execute('SELECT * FROM leases ORDER BY exp_sort')
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return jsonify(rows)

@app.route('/api/leases', methods=['POST'])
def add_lease():
    d = request.json; now = datetime.datetime.utcnow().isoformat()
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        'INSERT INTO leases (id,tenant,address,building,expiration,exp_sort,source,notes,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET tenant=EXCLUDED.tenant,address=EXCLUDED.address,building=EXCLUDED.building,expiration=EXCLUDED.expiration,exp_sort=EXCLUDED.exp_sort,source=EXCLUDED.source,notes=EXCLUDED.notes,updated_at=EXCLUDED.updated_at',
        (d.get('id'), d.get('tenant'), d.get('address'), d.get('building'),
         d.get('expiration'), d.get('exp_sort'), d.get('source'), d.get('notes'), now))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['PUT','OPTIONS'])
def update_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    d = request.json; now = datetime.datetime.utcnow().isoformat()
    conn = get_db(); cur = conn.cursor()
    cur.execute(
        'UPDATE leases SET tenant=%s,address=%s,building=%s,expiration=%s,exp_sort=%s,source=%s,notes=%s,updated_at=%s WHERE id=%s',
        (d.get('tenant'), d.get('address'), d.get('building'), d.get('expiration'),
         d.get('exp_sort'), d.get('source'), d.get('notes'), now, lid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/leases/<lid>', methods=['DELETE','OPTIONS'])
def delete_lease(lid):
    if request.method == 'OPTIONS':
        return jsonify({'ok': True})
    conn = get_db(); cur = conn.cursor()
    cur.execute('DELETE FROM leases WHERE id=%s', (lid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
