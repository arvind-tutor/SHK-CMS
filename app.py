from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
from datetime import *

app = Flask(__name__)
app.secret_key = 'shk-cms-secret-key'

# def connect_db():
#     return mysql.connector.connect(
#         host="sql12.freesqldatabase.com",
#         user="sql12780757",
#         password="SI5nLl7W1R",
#         database="sql12780757",
#         port=3306
#     )


def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="shkuser",
        password="shk1234",
        database="shk",
    )

def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cms (
            id INT PRIMARY KEY AUTO_INCREMENT,
            bank VARCHAR(10),
            cheque_no INT,
            amount INT,
            issue_date DATE,
            post_date DATE,
            vendor VARCHAR(50)
        );
    """)
    cursor.execute("SHOW COLUMNS FROM cms LIKE 'status_date'")
    result_date = cursor.fetchone()
    if not result_date:
        cursor.execute("ALTER TABLE cms ADD COLUMN status_date DATE")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(100) UNIQUE
    );
    """)
    conn.commit()
    conn.close()

@app.route('/')
def home():
    today = datetime.now().date()
    current_date = today.strftime("%d-%m-%Y")

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    # custom
    cursor.execute("SELECT COUNT(*) FROM cms")
    total_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    cursor.execute("SELECT COUNT(*) FROM cms WHERE status = %s", ("Active",))
    active_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    cursor.execute("SELECT COUNT(*) FROM cms WHERE status = %s", ("Cashed",))
    cashed_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    cursor.execute("SELECT COUNT(*) FROM cms WHERE status = %s", ("Cancelled",))
    cancelled_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    cursor.execute("SELECT COUNT(*) FROM cms WHERE status = %s", ("Bounced",))
    bounced_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    cursor.execute("SELECT COUNT(*) FROM cms WHERE status = %s", ("Mistake",))
    mistake_cheques = int(cursor.fetchone()['COUNT(*)'] or 0)

    # Prepare a list of 7 days
    days = []
    for i in range(7):
        day = today + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_display = day.strftime("%d-%m-%Y")
        # Fetch count and sum for that day
        cursor.execute("SELECT COUNT(*) as c, SUM(amount) as s FROM cms WHERE post_date = %s", (day_str,))
        result = cursor.fetchone()
        count = int(result['c'] or 0)
        amount = float(result['s'] or 0)
        days.append({'date': day_display, 'count': count, 'amount': amount})


    conn.close()

    return render_template(
        'index.html',
        current_date=current_date,
        days=days,
        ci=total_cheques,
        ca=active_cheques,
        cc=cashed_cheques,
        cn=cancelled_cheques,
        cb=bounced_cheques,
        cm=mistake_cheques,

    )
 
@app.route('/chequeentry', methods=['GET', 'POST'])
def index():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM vendors order by name asc")
    vendor_list = [row['name'] for row in cursor.fetchall()]

    if request.method == 'POST':
        bank=request.form['bank']
        chequeno = request.form['chqno']
        amount=request.form['amount']
        issuedate = request.form['idate']
        postdate = request.form['rdate']
        vendor=request.form['vendor']
        cursor.execute("SELECT * FROM cms WHERE cheque_no = %s", (chequeno,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            flash("❌ Error: Cheque number already exists!", "error")
            return redirect('/chequeentry')

        cursor.execute("INSERT INTO cms (bank,cheque_no,amount,issue_date,post_date,vendor) VALUES (%s, %s, %s, %s, %s, %s)",
                       (bank,chequeno,amount,issuedate,postdate,vendor))
        conn.commit()
        conn.close()
        flash("✅ Cheque added successfully!", "success")
        return redirect('/chequeentry')
    cursor.execute("SELECT * FROM cms order by ID desc limit 5")
    data = cursor.fetchall()
    conn.close()
    return render_template('chequeentry.html', records=data,vendor_list=vendor_list)

@app.route('/statusupdate', methods=['GET', 'POST'])
def statusupdate():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        cheque_no = request.form.get('cheque_no')

        # Search cheque details
        cursor.execute("SELECT * FROM cms WHERE cheque_no = %s", (cheque_no,))
        cheque = cursor.fetchone()
        conn.close()

        return render_template('statusupdate.html', cheque=cheque)

    return render_template('statusupdate.html', cheque=None)

@app.route('/updatestatus', methods=['POST'])
def updatestatus():
    cheque_no = request.form['cheque_no']
    new_status = request.form['status']
    status_date = request.form['status_date']

    conn = connect_db()
    cursor = conn.cursor()

    # Update the status and date
    cursor.execute("UPDATE cms SET status = %s, status_date = %s WHERE cheque_no = %s", (new_status, status_date, cheque_no))
    conn.commit()
    conn.close()

    flash(f"✅ Cheque {cheque_no} status updated to {new_status}!", "success")
    return redirect('/statusupdate')

@app.route('/search', methods=['GET', 'POST'])
def search():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT vendor FROM cms")
    vendor_list = [row['vendor'] for row in cursor.fetchall()]

    results = []
    total_cheques = 0
    active_cheques = 0
    total_amount = 0
    cashed_amount = 0
    active_amount = 0

    if request.method == 'POST':
        query = "SELECT * FROM cms WHERE 1=1"
        summary_query = "SELECT COUNT(*) as total_cheques, SUM(amount) as total_amount, SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) as active_cheques, SUM(CASE WHEN status='Cashed' THEN amount ELSE 0 END) as cashed_amount, SUM(CASE WHEN status='Active' THEN amount ELSE 0 END) as active_amount FROM cms WHERE 1=1"
        where_clauses = ""
        params = []

        bank = request.form.get('bank')
        vendor = request.form.get('vendor')
        cheque_no = request.form.get('cheque_no')
        from_date = request.form.get('from_date')
        to_date = request.form.get('to_date')

        if bank:
            where_clauses += " AND bank=%s"
            params.append(bank)
        if vendor:
            where_clauses += " AND vendor=%s"
            params.append(vendor)
        if cheque_no:
            where_clauses += " AND cheque_no=%s"
            params.append(cheque_no)
        if from_date and to_date:
            where_clauses += " AND post_date BETWEEN %s AND %s"
            params.append(from_date)
            params.append(to_date)

        # Final Queries
        cursor.execute(query + where_clauses, tuple(params))
        results = cursor.fetchall()

        cursor.execute(summary_query + where_clauses, tuple(params))
        summary = cursor.fetchone()
        total_cheques = summary['total_cheques'] or 0
        total_amount = summary['total_amount'] or 0
        active_cheques = summary['active_cheques'] or 0
        cashed_amount = summary['cashed_amount'] or 0
        active_amount = summary['active_amount'] or 0

    conn.close()
    return render_template('search.html', vendor_list=vendor_list, results=results,
                           total_cheques=total_cheques, active_cheques=active_cheques,
                           total_amount=total_amount, cashed_amount=cashed_amount,
                           active_amount=active_amount)



@app.route('/vendor', methods=['GET', 'POST'])
def vendor():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['vendor_name']
        try:
            cursor.execute("INSERT INTO vendors (name) VALUES (%s)", (name,))
            conn.commit()
            flash(f"✅ Vendor '{name}' added successfully!", "success")
        except mysql.connector.IntegrityError:
            flash(f"❌ Vendor '{name}' already exists!", "error")

    cursor.execute("SELECT * FROM vendors")
    vendors = cursor.fetchall()

    conn.close()
    return render_template('vendor.html', vendors=vendors)


# if __name__ == '__main__':
#     init_db()  # create table
#     app.run(debug=False, host='0.0.0.0', port=10000)


if __name__ == '__main__':
    app.run(debug=True)
