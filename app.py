from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import qrcode
import os
from datetime import datetime, timedelta
import secrets
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this!

# Database setup
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Members table
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  password TEXT NOT NULL)''')
    
    # QR codes table
    c.execute('''CREATE TABLE IF NOT EXISTS qr_codes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  qr_token TEXT UNIQUE NOT NULL,
                  created_at DATETIME NOT NULL,
                  expires_at DATETIME NOT NULL,
                  is_active INTEGER DEFAULT 1)''')
    
    # Attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  member_id TEXT NOT NULL,
                  member_name TEXT NOT NULL,
                  qr_token TEXT NOT NULL,
                  marked_at DATETIME NOT NULL,
                  FOREIGN KEY(member_id) REFERENCES members(member_id))''')
    
    # Create default admin account (username: admin, password: admin123)
    # Create some demo members
    try:
        c.execute("INSERT INTO members (member_id, name, password) VALUES (?, ?, ?)",
                  ('ADMIN', 'Administrator', 'admin123'))
        c.execute("INSERT INTO members (member_id, name, password) VALUES (?, ?, ?)",
                  ('M001', 'Ahmed Ali', 'pass123'))
        c.execute("INSERT INTO members (member_id, name, password) VALUES (?, ?, ?)",
                  ('M002', 'Hassan Khan', 'pass123'))
        c.execute("INSERT INTO members (member_id, name, password) VALUES (?, ?, ?)",
                  ('M003', 'Usman Ahmed', 'pass123'))
    except:
        pass  # Already exists
    
    conn.commit()
    conn.close()

init_db()

# Helper functions
def get_db():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_qr_valid(qr_token):
    """Check if QR code is valid (exists and not expired)"""
    conn = get_db()
    qr = conn.execute('SELECT * FROM qr_codes WHERE qr_token = ? AND is_active = 1',
                      (qr_token,)).fetchone()
    conn.close()
    
    if not qr:
        return False
    
    expires_at = datetime.strptime(qr['expires_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > expires_at:
        return False
    
    return True

def has_marked_attendance(member_id, qr_token):
    """Check if member already marked attendance for this QR"""
    conn = get_db()
    record = conn.execute('SELECT * FROM attendance WHERE member_id = ? AND qr_token = ?',
                          (member_id, qr_token)).fetchone()
    conn.close()
    return record is not None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# ADMIN ROUTES
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple admin check (you can make this more secure)
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    
    # Get current active QR code
    current_qr = conn.execute('''SELECT * FROM qr_codes 
                                 WHERE is_active = 1 
                                 ORDER BY created_at DESC LIMIT 1''').fetchone()
    
    # Get last 2 days attendance for display on dashboard
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    attendance_records = conn.execute('''SELECT * FROM attendance 
                                         WHERE marked_at >= ? 
                                         ORDER BY marked_at DESC''',
                                      (two_days_ago,)).fetchall()
    
    # Get total count for last 10 days for stats
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
    total_attendance = conn.execute('''SELECT COUNT(*) as count FROM attendance 
                                       WHERE marked_at >= ?''',
                                    (ten_days_ago,)).fetchone()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          current_qr=current_qr, 
                          attendance_records=attendance_records,
                          total_count=total_attendance['count'] if total_attendance else 0)

@app.route('/admin/generate-qr', methods=['POST'])
def generate_qr():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Deactivate old QR codes
    conn = get_db()
    conn.execute('UPDATE qr_codes SET is_active = 0')
    
    # Generate new QR token
    qr_token = secrets.token_urlsafe(16)
    created_at = datetime.now()
    expires_at = created_at + timedelta(hours=2)  # 2 hour expiry
    
    # Save to database
    conn.execute('''INSERT INTO qr_codes (qr_token, created_at, expires_at, is_active)
                    VALUES (?, ?, ?, 1)''',
                 (qr_token, created_at.strftime('%Y-%m-%d %H:%M:%S'),
                  expires_at.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    # Generate QR code image
    qr_data = f"ATTENDANCE:{qr_token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    qr_path = f'static/qr_codes/qr_{qr_token}.png'
    img.save(qr_path)
    
    flash(f'New QR code generated! Expires at {expires_at.strftime("%I:%M %p")}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export-csv')
def export_csv():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
    records = conn.execute('''SELECT member_id, member_name, marked_at 
                              FROM attendance 
                              WHERE marked_at >= ? 
                              ORDER BY marked_at DESC''',
                           (ten_days_ago,)).fetchall()
    conn.close()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Member ID', 'Member Name', 'Timestamp'])
    
    for record in records:
        writer.writerow([record['member_id'], record['member_name'], record['marked_at']])
    
    output.seek(0)
    
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=attendance_{datetime.now().strftime("%Y%m%d")}.csv'
    }

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('admin_login'))

# MEMBER ROUTES
@app.route('/member/login', methods=['GET', 'POST'])
def member_login():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        password = request.form.get('password')
        
        conn = get_db()
        member = conn.execute('SELECT * FROM members WHERE member_id = ? AND password = ?',
                             (member_id, password)).fetchone()
        conn.close()
        
        if member and member['member_id'] != 'ADMIN':
            session['member_logged_in'] = True
            session['member_id'] = member['member_id']
            session['member_name'] = member['name']
            flash('Login successful!', 'success')
            return redirect(url_for('member_scan'))
        else:
            flash('Invalid Member ID or Password!', 'danger')
    
    return render_template('member_login.html')

@app.route('/member/scan')
def member_scan():
    if not session.get('member_logged_in'):
        return redirect(url_for('member_login'))
    
    return render_template('member_scan.html')

@app.route('/member/dashboard')
def member_dashboard():
    if not session.get('member_logged_in'):
        return redirect(url_for('member_login'))
    
    member_id = session.get('member_id')
    
    # Get member's attendance history (last 30 days)
    conn = get_db()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    my_attendance = conn.execute('''SELECT * FROM attendance 
                                    WHERE member_id = ? AND marked_at >= ?
                                    ORDER BY marked_at DESC''',
                                 (member_id, thirty_days_ago)).fetchall()
    conn.close()
    
    return render_template('member_dashboard.html', my_attendance=my_attendance)

@app.route('/member/mark-attendance', methods=['POST'])
def mark_attendance():
    if not session.get('member_logged_in'):
        return redirect(url_for('member_login'))
    
    qr_data = request.form.get('qr_data')
    
    # Extract token from QR data
    if not qr_data or not qr_data.startswith('ATTENDANCE:'):
        flash('Invalid QR code!', 'danger')
        return redirect(url_for('member_scan'))
    
    qr_token = qr_data.replace('ATTENDANCE:', '')
    
    # Check if QR is valid
    if not check_qr_valid(qr_token):
        flash('QR code expired or invalid!', 'danger')
        return redirect(url_for('member_scan'))
    
    member_id = session.get('member_id')
    member_name = session.get('member_name')
    
    # Check if already marked
    if has_marked_attendance(member_id, qr_token):
        flash('You have already marked attendance for this session!', 'warning')
        return redirect(url_for('member_scan'))
    
    # Mark attendance
    conn = get_db()
    conn.execute('''INSERT INTO attendance (member_id, member_name, qr_token, marked_at)
                    VALUES (?, ?, ?, ?)''',
                 (member_id, member_name, qr_token, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()
    
    flash('Attendance marked successfully!', 'success')
    return redirect(url_for('member_scan'))

@app.route('/member/logout')
def member_logout():
    session.pop('member_logged_in', None)
    session.pop('member_id', None)
    session.pop('member_name', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('member_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
