from flask import Flask, render_template, request, redirect, flash, url_for
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "shk-cms-secret-key"

# ---------- DB ----------
def connect_db():
    # Adjust creds for your environment
    return mysql.connector.connect(
        host="localhost",
        user="shkuser",
        password="shk1234",
        database="shk",
        autocommit=False,
    )

def init_db():
    conn = connect_db()
    cur = conn.cursor()

    # Core CMS table (minimal, we evolve columns below if missing)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cms (
            id INT PRIMARY KEY AUTO_INCREMENT,
            bank VARCHAR(32),
            cheque_no BIGINT,
            amount DECIMAL(12,2),
            issue_date DATE,
            post_date DATE,
            vendor VARCHAR(100)
        );
    """)

    # Add missing columns (status, status_date) if needed
    cur.execute("SHOW COLUMNS FROM cms LIKE 'status'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE cms ADD COLUMN status VARCHAR(20) DEFAULT 'Active'")
        # Backfill existing rows as Active
        cur.execute("UPDATE cms SET status = COALESCE(status, 'Active')")

    cur.execute("SHOW COLUMNS FROM cms LIKE 'status_date'")
    if not cur.fetchone():
        cur.execute("ALTER TABLE cms ADD COLUMN status_date DATE")

    # Vendors table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) UNIQUE
        );
    """)
    conn.commit()
    conn.close()

# ---------- Routes ----------
@app.route("/")
def home():
    """
    Dashboard: status counts + 7-day amount chart/table
    """
    today = datetime.now().date()

    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Totals
    cur.execute("SELECT COUNT(*) AS c FROM cms")
    total_cheques = int(cur.fetchone().get("c") or 0)

    def count_status(s):
        cur.execute("SELECT COUNT(*) AS c FROM cms WHERE status = %s", (s,))
        return int(cur.fetchone().get("c") or 0)

    active_cheques    = count_status("Active")
    cashed_cheques    = count_status("Cashed")
    cancelled_cheques = count_status("Cancelled")
    bounced_cheques   = count_status("Bounced")
    mistake_cheques   = count_status("Mistake")

    # 7 days (today → next 6)
    days = []
    for i in range(7):
        d = today + timedelta(days=i)
        d_sql = d.strftime("%Y-%m-%d")
        d_disp = d.strftime("%d-%m-%Y")
        cur.execute("SELECT COUNT(*) AS c, SUM(amount) AS s FROM cms WHERE post_date = %s", (d_sql,))
        row = cur.fetchone() or {}
        count = int(row.get("c") or 0)
        amount = float(row.get("s") or 0)
        days.append({"date": d_disp, "count": count, "amount": amount})

    conn.close()

    return render_template(
        "index.html",
        days=days,
        ci=total_cheques,
        ca=active_cheques,
        cc=cashed_cheques,
        cn=cancelled_cheques,
        cb=bounced_cheques,
        cm=mistake_cheques,
    )

@app.route("/chequeentry", methods=["GET", "POST"])
def chequeentry():
    """
    Create cheque + show last 5 entries
    """
    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Vendor dropdown from vendors table (sorted)
    cur.execute("SELECT name FROM vendors ORDER BY name ASC")
    vendor_list = [r["name"] for r in cur.fetchall()]

    if request.method == "POST":
        bank      = (request.form.get("bank") or "").strip()
        chqno     = (request.form.get("chqno") or "").strip()
        amount    = (request.form.get("amount") or "").strip()
        issuedate = (request.form.get("idate") or "").strip()
        postdate  = (request.form.get("rdate") or "").strip()
        vendor    = (request.form.get("vendor") or "").strip()

        # Duplicate check on cheque_no for safety
        cur.execute("SELECT id FROM cms WHERE cheque_no = %s", (chqno,))
        if cur.fetchone():
            conn.close()
            flash("❌ Error: Cheque number already exists!", "error")
            return redirect(url_for("chequeentry"))

        cur.execute(
            """INSERT INTO cms (bank, cheque_no, amount, issue_date, post_date, vendor, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'Active')""",
            (bank, chqno, amount, issuedate, postdate, vendor),
        )
        conn.commit()
        conn.close()
        flash("✅ Cheque added successfully!", "success")
        return redirect(url_for("chequeentry"))

    # Last 5 cheques
    cur.execute("SELECT * FROM cms ORDER BY id DESC LIMIT 5")
    records = cur.fetchall()
    conn.close()
    return render_template("chequeentry.html", records=records, vendor_list=vendor_list)

@app.route("/statusupdate", methods=["GET", "POST"])
def statusupdate():
    """
    Search cheque by number and show update actions
    """
    cheque = None
    if request.method == "POST":
        cheque_no = (request.form.get("cheque_no") or "").strip()
        conn = connect_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM cms WHERE cheque_no = %s", (cheque_no,))
        cheque = cur.fetchone()
        conn.close()
    return render_template("statusupdate.html", cheque=cheque)

@app.route("/updatestatus", methods=["POST"])
def updatestatus():
    """
    Persist status change
    """
    cheque_no   = (request.form.get("cheque_no") or "").strip()
    new_status  = (request.form.get("status") or "").strip()
    status_date = (request.form.get("status_date") or "").strip()

    if not (cheque_no and new_status and status_date):
        flash("❌ Missing fields to update status.", "error")
        return redirect(url_for("statusupdate"))

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE cms SET status = %s, status_date = %s WHERE cheque_no = %s",
        (new_status, status_date, cheque_no),
    )
    conn.commit()
    conn.close()

    flash(f"✅ Cheque {cheque_no} status updated to {new_status}!", "success")
    return redirect(url_for("statusupdate"))

@app.route("/search", methods=["GET", "POST"])
def search():
    """
    Filter cheques + summary cards
    """
    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    # Vendor dropdown from vendors table for consistency
    cur.execute("SELECT name FROM vendors ORDER BY name ASC")
    vendor_list = [r["name"] for r in cur.fetchall()]

    results = []
    total_cheques = active_cheques = 0
    total_amount = cashed_amount = active_amount = 0

    if request.method == "POST":
        base = "FROM cms WHERE 1=1"
        where = []
        params = []

        bank      = (request.form.get("bank") or "").strip()
        vendor    = (request.form.get("vendor") or "").strip()
        cheque_no = (request.form.get("cheque_no") or "").strip()
        dfrom     = (request.form.get("from_date") or "").strip()
        dto       = (request.form.get("to_date") or "").strip()

        if bank:
            where.append("bank = %s"); params.append(bank)
        if vendor:
            where.append("vendor = %s"); params.append(vendor)
        if cheque_no:
            where.append("cheque_no = %s"); params.append(cheque_no)
        if dfrom and dto:
            where.append("post_date BETWEEN %s AND %s"); params.extend([dfrom, dto])

        where_sql = (" AND " + " AND ".join(where)) if where else ""

        # Results
        cur.execute(f"SELECT * {base}{where_sql} ORDER BY post_date DESC, id DESC", tuple(params))
        results = cur.fetchall()

        # Summary
        cur.execute(
            f"""SELECT
                    COUNT(*) AS total_cheques,
                    SUM(amount) AS total_amount,
                    SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) AS active_cheques,
                    SUM(CASE WHEN status='Cashed' THEN amount ELSE 0 END) AS cashed_amount,
                    SUM(CASE WHEN status='Active' THEN amount ELSE 0 END) AS active_amount
                {base}{where_sql}""",
            tuple(params)
        )
        s = cur.fetchone() or {}
        total_cheques = int(s.get("total_cheques") or 0)
        total_amount  = float(s.get("total_amount") or 0)
        active_cheques = int(s.get("active_cheques") or 0)
        cashed_amount  = float(s.get("cashed_amount") or 0)
        active_amount  = float(s.get("active_amount") or 0)

    conn.close()

    return render_template(
        "search.html",
        vendor_list=vendor_list,
        results=results,
        total_cheques=total_cheques,
        active_cheques=active_cheques,
        total_amount=total_amount,
        cashed_amount=cashed_amount,
        active_amount=active_amount,
    )

@app.route("/vendor", methods=["GET", "POST"])
def vendor():
    """
    Add vendor + list vendors
    """
    conn = connect_db()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = (request.form.get("vendor_name") or "").strip()
        if not name:
            flash("❌ Vendor name is required.", "error")
        else:
            try:
                cur.execute("INSERT INTO vendors (name) VALUES (%s)", (name,))
                conn.commit()
                flash(f"✅ Vendor '{name}' added successfully!", "success")
            except mysql.connector.IntegrityError:
                conn.rollback()
                flash(f"❌ Vendor '{name}' already exists!", "error")

    cur.execute("SELECT * FROM vendors ORDER BY name ASC")
    vendors = cur.fetchall()
    conn.close()
    return render_template("vendor.html", vendors=vendors)

# ---------- Main ----------
# if __name__ == "__main__":
#     init_db()
#     # For production, run via Gunicorn; debug=True is for local dev
#     app.run(debug=True, host="0.0.0.0", port=10000)


if __name__ == '__main__':
    app.run(debug=True)
