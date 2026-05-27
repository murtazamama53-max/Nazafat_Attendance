from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import qrcode
import os
from datetime import datetime, timedelta
import secrets
import csv
from io import StringIO
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.secret_key = 'jamaat_secure_system_2026_murtaza'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'attendance.db')
QR_FOLDER = os.path.join(BASE_DIR, 'static', 'qr_codes')

if not os.path.exists(QR_FOLDER): os.makedirs(QR_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT UNIQUE,
                  name TEXT, password TEXT, role TEXT DEFAULT 'member')''')
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, is_active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS qr_codes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, qr_token TEXT, event_id INTEGER,
                  created_at DATETIME, expires_at DATETIME, is_active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, member_name TEXT,
                  event_name TEXT, event_id INTEGER, lat REAL, lon REAL, location_address TEXT, marked_at DATETIME)''')

    users = [
        ('MURTAZA', 'Murtaza Muzaffar', generate_password_hash('2005'), 'superadmin'),
        ('Admin', 'Secondary Admin', generate_password_hash('sec1'), 'admin')
    ]
    for mid, name, pwd, role in users:
        try:
            c.execute("INSERT INTO members (member_id, name, password, role) VALUES (?,?,?,?)", (mid, name, pwd, role))
        except:
            pass
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        mid = request.form.get('member_id').strip()
        pwd = request.form.get('password')
        conn = get_db()
        user = conn.execute('SELECT * FROM members WHERE member_id = ? AND role IN ("superadmin", "admin")', (mid,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], pwd):
            session.permanent = True
            session['user_id'] = user['member_id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('admin_dashboard'))
        flash('Unauthorized Admin Access', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] not in ['superadmin', 'admin']:
        return redirect(url_for('admin_login'))

    filter_type = request.args.get('filter', 'all')
    conn = get_db()
    query = 'SELECT * FROM attendance'
    params = []

    if filter_type == 'day':
        query += ' WHERE marked_at >= ?'
        params.append((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'))
    elif filter_type == 'week':
        query += ' WHERE marked_at >= ?'
        params.append((datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S'))

    query += ' ORDER BY marked_at DESC LIMIT 100'

    records = conn.execute(query, params).fetchall()
    events = conn.execute('SELECT * FROM events ORDER BY id DESC').fetchall()
    current_qr = conn.execute('SELECT * FROM qr_codes WHERE is_active = 1 ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()

    return render_template('admin_dashboard.html', events=events, current_qr=current_qr, records=records, current_filter=filter_type)

@app.route('/admin/create-event', methods=['POST'])
def create_event():
    if session.get('role') != 'superadmin': return "Unauthorized", 403
    name = request.form.get('event_name')
    conn = get_db()
    conn.execute('INSERT INTO events (name, date) VALUES (?, ?)', (name, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    flash('Event Created Successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/generate-qr', methods=['POST'])
def generate_qr():
    if 'role' not in session: return redirect(url_for('admin_login'))
    event_id = request.form.get('event_id')
    conn = get_db()
    conn.execute('UPDATE qr_codes SET is_active = 0')
    token = secrets.token_urlsafe(16)
    created = datetime.now()
    expires = created + timedelta(hours=2)
    conn.execute('INSERT INTO qr_codes (qr_token, event_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
                 (token, event_id, created, expires))
    conn.commit()
    qr = qrcode.make(f"ATTENDANCE:{token}")
    qr.save(os.path.join(QR_FOLDER, f"qr_{token}.png"))
    conn.close()
    flash(f'QR Generated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-qr', methods=['POST'])
def delete_qr():
    if session.get('role') != 'superadmin': return "Unauthorized", 403
    conn = get_db()
    current_qr = conn.execute('SELECT * FROM qr_codes WHERE is_active = 1').fetchone()
    if current_qr:
        conn.execute('UPDATE qr_codes SET is_active = 0 WHERE qr_token = ?', (current_qr['qr_token'],))
        conn.commit()
        qr_file = os.path.join(QR_FOLDER, f"qr_{current_qr['qr_token']}.png")
        if os.path.exists(qr_file): os.remove(qr_file)
        flash('QR Code Deleted!', 'info')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-attendance/<int:id>', methods=['POST'])
def delete_attendance(id):
    if session.get('role') != 'superadmin': return "Unauthorized", 403
    conn = get_db()
    conn.execute('DELETE FROM attendance WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Record deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-member', methods=['POST'])
def add_member():
    if session.get('role') != 'superadmin': return "Unauthorized", 403
    mid = request.form.get('member_id').upper().strip()
    name = request.form.get('name')
    pwd = generate_password_hash(request.form.get('password'))
    conn = get_db()
    try:
        conn.execute('INSERT INTO members (member_id, name, password, role) VALUES (?, ?, ?, "member")', (mid, name, pwd))
        conn.commit()
        flash(f'Member {name} Registered!', 'success')
    except:
        flash('Member ID already exists!', 'danger')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export-csv')
def export_csv():
    if session.get('role') != 'superadmin': return "Unauthorized", 403
    conn = get_db()
    records = conn.execute('SELECT member_id, member_name, event_name, lat, lon, marked_at FROM attendance ORDER BY marked_at DESC').fetchall()
    conn.close()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Member ID', 'Name', 'Event', 'Latitude', 'Longitude', 'Timestamp'])
    for r in records:
        writer.writerow([r['member_id'], r['member_name'], r['event_name'], r['lat'], r['lon'], r['marked_at']])
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=attendance_{datetime.now().strftime("%Y%m%d")}.csv'
    }

@app.route('/api/get-address')
def get_address():
    lat, lon = request.args.get('lat'), request.args.get('lon')
    if not lat or not lon: return jsonify({'address': 'No GPS'})
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {'User-Agent': 'JamaatApp/1.0'}
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            addr = data.get('address', {})
            parts = [addr.get(k) for k in ['road', 'suburb', 'city'] if addr.get(k)]
            return jsonify({'address': ', '.join(parts[:3]) if parts else f"{lat}, {lon}"})
        return jsonify({'address': f"{lat}, {lon}"})
    except: return jsonify({'address': f"{lat}, {lon}"})

@app.route('/member/login', methods=['GET', 'POST'])
def member_login():
    if request.method == 'POST':
        mid = request.form.get('member_id').upper().strip()
        pwd = request.form.get('password')
        conn = get_db()
        user = conn.execute('SELECT * FROM members WHERE member_id = ? AND role = "member"', (mid,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], pwd):
            session.permanent = True
            session['user_id'], session['user_name'], session['role'] = user['member_id'], user['name'], user['role']
            return redirect(url_for('member_dashboard'))
        flash('Invalid Credentials', 'danger')
    return render_template('member_login.html')

@app.route('/member/dashboard')
def member_dashboard():
    if 'user_id' not in session: return redirect(url_for('member_login'))
    conn = get_db()
    my_records = conn.execute('SELECT * FROM attendance WHERE member_id = ? ORDER BY marked_at DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('member_dashboard.html', records=my_records)

@app.route('/member/scan')
def member_scan():
    if 'user_id' not in session: return redirect(url_for('member_login'))
    return render_template('member_scan.html')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    qr_data = request.form.get('qr_data', '').replace('ATTENDANCE:', '')
    lat, lon = request.form.get('lat'), request.form.get('lon')
    conn = get_db()
    qr = conn.execute('SELECT q.*, e.name as ev_name FROM qr_codes q JOIN events e ON q.event_id = e.id WHERE q.qr_token = ? AND q.is_active = 1', (qr_data,)).fetchone()

    if not qr:
        flash('Invalid QR!', 'danger')
        conn.close()
        return redirect(url_for('member_dashboard'))

    try: expires_at = datetime.strptime(qr['expires_at'], '%Y-%m-%d %H:%M:%S.%f')
    except: expires_at = datetime.strptime(qr['expires_at'], '%Y-%m-%d %H:%M:%S')

    if datetime.now() > expires_at:
        flash('QR Expired!', 'warning'); conn.close()
        return redirect(url_for('member_dashboard'))

    five_hours_ago = (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
    recent = conn.execute('SELECT id FROM attendance WHERE member_id = ? AND event_id = ? AND marked_at >= ?', (session['user_id'], qr['event_id'], five_hours_ago)).fetchone()

    if recent:
        flash('Already marked!', 'warning'); conn.close()
        return redirect(url_for('member_dashboard'))

    conn.execute('INSERT INTO attendance (member_id, member_name, event_name, event_id, lat, lon, marked_at) VALUES (?,?,?,?,?,?,?)',
                 (session['user_id'], session['user_name'], qr['ev_name'], qr['event_id'], lat, lon, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    flash('Attendance Marked! ✅', 'success')
    return redirect(url_for('member_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
