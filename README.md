# 🕌 Jamaat Attendance System

A complete QR-based attendance tracking system for your jamaat organization.

## ✨ Features

### For Admin:
- 🔐 Secure admin login
- 📱 Generate QR codes (expires in 2 hours)
- 📊 View last 2 days attendance on dashboard
- 📥 Export last 10 days data to CSV
- 📈 Real-time attendance statistics

### For Members:
- 🔐 Member login with ID and password
- 📷 Scan QR code with phone camera
- 👤 View personal attendance history (last 30 days)
- ✅ Automatic duplicate prevention

---

## 📋 Requirements

- Python 3.8 or higher
- A phone with camera (for members)
- Computer/laptop (for admin)

---

## 🚀 Quick Start (Local Testing)

### Step 1: Install Python
1. Download from https://www.python.org/downloads/
2. During installation, CHECK ✅ "Add Python to PATH"

### Step 2: Setup the App
1. Download/extract this folder
2. Open Command Prompt (Windows) or Terminal (Mac/Linux)
3. Navigate to the folder:
   ```
   cd path/to/jamaat_attendance_app
   ```

4. Install required packages:
   ```
   pip install -r requirements.txt
   ```

### Step 3: Run the App
```
python app.py
```

You'll see:
```
* Running on http://127.0.0.1:5000
```

### Step 4: Open in Browser
- On your computer: http://localhost:5000
- On your phone (same WiFi): http://YOUR_COMPUTER_IP:5000

---

## 👥 Default Login Credentials

### Admin Login:
- Username: `admin`
- Password: `admin123`

### Demo Members:
- Member ID: `M001`, Password: `pass123`
- Member ID: `M002`, Password: `pass123`
- Member ID: `M003`, Password: `pass123`

⚠️ **IMPORTANT:** Change these passwords before real use!

---

## 🌐 Deploy Online (PythonAnywhere - FREE)

### Why PythonAnywhere?
- ✅ Free tier available
- ✅ Specifically built for Python/Flask apps
- ✅ No credit card needed
- ✅ Your app runs 24/7

### Deployment Steps:

#### 1. Create Account
- Go to https://www.pythonanywhere.com
- Sign up for FREE Beginner account

#### 2. Upload Files
- Click "Files" tab
- Upload all files from this folder:
  - `app.py`
  - `requirements.txt`
  - `templates/` folder (all HTML files)
  - `static/` folder (create empty `qr_codes` folder inside)

#### 3. Install Packages
- Go to "Consoles" tab
- Start a new "Bash" console
- Run:
  ```bash
  pip3 install --user -r requirements.txt
  ```

#### 4. Configure Web App
- Go to "Web" tab
- Click "Add a new web app"
- Choose "Flask"
- Python version: 3.10
- Path to Flask app: `/home/YOUR_USERNAME/app.py`
- Click on "WSGI configuration file" link
- Find this line:
  ```python
  from flask_app import app as application
  ```
- Replace with:
  ```python
  from app import app as application
  ```

#### 5. Go Live!
- Click green "Reload" button
- Your app is now live at: `http://YOUR_USERNAME.pythonanywhere.com`

---

## 📱 How to Use

### For Admin (You):

1. **Login** → Go to your app URL → Click "Admin Login"
2. **Generate QR** → Click "Generate New QR Code" button
3. **Show QR** → Display the QR code on your screen/projector
4. **Monitor** → Watch attendance appear in real-time
5. **Export** → Click "Export Last 10 Days (CSV)" to download data

### For Members:

1. **Login** → Go to app URL on phone → Click "Member Login"
2. **Scan** → Point camera at admin's QR code
3. **Confirm** → Attendance marked automatically!
4. **Check** → Click "My Attendance" to see history

---

## 🔧 Customization Guide

### Add New Members:
Edit `app.py`, find `init_db()` function, add:
```python
c.execute("INSERT INTO members (member_id, name, password) VALUES (?, ?, ?)",
          ('M004', 'New Member Name', 'password123'))
```

### Change Admin Password:
In `app.py`, find `/admin/login` route, change:
```python
if username == 'admin' and password == 'YOURNEWPASSWORD':
```

### Change QR Expiry Time:
In `app.py`, find `generate_qr` route, change:
```python
expires_at = created_at + timedelta(hours=4)  # Now 4 hours
```

---

## 📊 Database Structure

The app uses SQLite (file: `attendance.db`)

### Tables:
1. **members** - Member credentials
2. **qr_codes** - Generated QR codes with expiry
3. **attendance** - All attendance records

---

## 🐛 Troubleshooting

### Camera not working?
- Allow camera permissions in browser
- Use manual QR data entry option
- Make sure using HTTPS (required for camera)

### QR code not generating?
- Check `static/qr_codes/` folder exists
- Check folder write permissions

### Can't access from phone?
- Make sure phone and computer on same WiFi
- Find computer IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
- Use IP like: `http://192.168.1.100:5000`

### Members can't login?
- Check member credentials in database
- Default demo members: M001, M002, M003 (password: pass123)

---

## 📁 Project Structure

```
jamaat_attendance_app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python packages
├── attendance.db          # Database (auto-created)
├── static/
│   ├── css/              # Stylesheets (optional)
│   └── qr_codes/         # Generated QR images
└── templates/
    ├── index.html        # Homepage
    ├── admin_login.html  # Admin login page
    ├── admin_dashboard.html  # Admin dashboard
    ├── member_login.html     # Member login page
    ├── member_scan.html      # QR scanner page
    └── member_dashboard.html # Member attendance history
```

---

## 🔒 Security Notes

⚠️ **Before Real Use:**
1. Change admin password in code
2. Change Flask secret_key in `app.py`
3. Use HTTPS in production (PythonAnywhere provides this)
4. Never share database file publicly

---

## 💡 Tips

- **Best Practice:** Generate new QR code for each duty/session
- **Backup:** Export CSV daily to keep records safe
- **Testing:** Test with demo members before real deployment
- **WiFi:** Make sure members can access the URL from their phones

---

## 📞 Support

If you face issues:
1. Check this README first
2. Google the exact error message
3. Ask on Flask forums/Stack Overflow

---

## 📜 License

Free to use for your jamaat organization. May Allah accept your efforts! 🤲

---

**Made with ❤️ for Jamaat Organization Management**
