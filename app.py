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
        user="root",
        password="qwerty@123",
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

    # Ranges
    day_15 = today + timedelta(days=15)
    day_30 = today + timedelta(days=30)
    day_45 = today + timedelta(days=45)

    # Format for SQL
    today_str = today.strftime("%Y-%m-%d")
    day_15_str = day_15.strftime("%Y-%m-%d")
    day_30_str = day_30.strftime("%Y-%m-%d")
    day_45_str = day_45.strftime("%Y-%m-%d")

    # Format for display
    current_date = today.strftime("%d-%m-%Y")
    display_15 = day_15.strftime("%d-%m-%Y")
    display_30 = day_30.strftime("%d-%m-%Y")
    display_45 = day_45.strftime("%d-%m-%Y")

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Today to 15 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (today_str, day_15_str))
    range1 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (today_str, day_15_str))
    result1 = cursor.fetchone()
    a = int (result1['COUNT(*)'] or 0)
    b = float (result1['SUM(amount)'] or 0)
    # 16 to 30 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (day_15_str, day_30_str))
    range2 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (day_15_str, day_30_str))
    result2 = cursor.fetchone()
    c = int (result2['COUNT(*)'] or 0)
    d = float (result2['SUM(amount)'] or 0)

    # 31 to 45 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (day_30_str, day_45_str))
    range3 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (day_30_str, day_45_str))
    result3 = cursor.fetchone()
    e = int (result3['COUNT(*)'] or 0)
    f = float (result3['SUM(amount)'] or 0)

    conn.close()

    return render_template(
        'index.html',
        current_date=current_date,
        display_15=display_15,
        display_30=display_30,
        display_45=display_45,
        range1=range1,
        range2=range2,
        range3=range3,
        count1=a,
        total1=b,
        count2=c,
        total2=d,
        count3=e,
        total3=f,
    )

@app.route('/custom', methods=['POST'])
def custom_range():
    from_date = request.form['from_date']
    to_date = request.form['to_date']

    from_display = datetime.strptime(from_date, "%Y-%m-%d").strftime("%d-%m-%Y")
    to_display = datetime.strptime(to_date, "%Y-%m-%d").strftime("%d-%m-%Y")

    today = datetime.now().date()
    day_15 = today + timedelta(days=15)
    day_30 = today + timedelta(days=30)
    day_45 = today + timedelta(days=45)

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Custom range
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (from_date, to_date))
    custom_results = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (from_date, to_date))
    result4 = cursor.fetchone()
    g = int (result4['COUNT(*)'] or 0)
    h = float (result4['SUM(amount)'] or 0)

    # Today to 15 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (today, day_15))
    range1 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (today, day_15))
    result1 = cursor.fetchone()
    a = int (result1['COUNT(*)'] or 0)
    b = float (result1['SUM(amount)'] or 0)
    # 16 to 30 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (day_15, day_30))
    range2 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (day_15, day_30))
    result2 = cursor.fetchone()
    c = int (result2['COUNT(*)'] or 0)
    d = float (result2['SUM(amount)'] or 0)

    # 31 to 45 days
    cursor.execute("SELECT * FROM cms WHERE post_date BETWEEN %s AND %s", (day_30, day_45))
    range3 = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE post_date BETWEEN %s AND %s", (day_30, day_45))
    result3 = cursor.fetchone()
    e = int (result3['COUNT(*)'] or 0)
    f = float (result3['SUM(amount)'] or 0)

    
    conn.close()

    return render_template(
        'index.html',
        current_date=today.strftime("%d-%m-%Y"),
        display_15=day_15.strftime("%d-%m-%Y"),
        display_30=day_30.strftime("%d-%m-%Y"),
        display_45=day_45.strftime("%d-%m-%Y"),
        range1=range1,
        range2=range2,
        range3=range3,
        count1=a,
        total1=b,
        count2=c,
        total2=d,
        count3=e,
        total3=f,
        count4=g,
        total4=h,
        custom_results=custom_results,
        from_display=from_display,
        to_display=to_display
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

@app.route('/search', methods=['GET', 'POST'])
def search():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch vendor list
    cursor.execute("SELECT name FROM vendors ORDER BY name ASC")
    vendor_list = [row['name'] for row in cursor.fetchall()]

    if request.method == 'POST':
        vendor = request.form['vendor']
        from_date = request.form['from_date']
        to_date = request.form['to_date']

        from_display = datetime.strptime(from_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        to_display = datetime.strptime(to_date, "%Y-%m-%d").strftime("%d-%m-%Y")

        cursor.execute("SELECT * FROM cms WHERE vendor= %s and post_date BETWEEN %s AND %s", (vendor,from_date, to_date))
        vendor_results = cursor.fetchall()
        cursor.execute("SELECT COUNT(*), SUM(amount) FROM cms WHERE vendor= %s and post_date BETWEEN %s AND %s", (vendor,from_date, to_date))
        result5 = cursor.fetchone()
        count5 = int(result5['COUNT(*)'] or 0)
        total5 = float(result5['SUM(amount)'] or 0)
        
        conn.close()
        return render_template(
            'search.html',
            count5=count5,
            total5=total5,
            vendor=vendor,
            vendor_results=vendor_results,
            from_display=from_display,
            to_display=to_display,
            vendor_list=vendor_list  # pass vendor list here
        )
    else:
        conn.close()
        # For GET request, show form with vendors
        return render_template('search.html', vendor_results=[], count5=0, total5=0, vendor="", from_display="", to_display="", vendor_list=vendor_list)

@app.route('/searchcheque', methods=['GET', 'POST'])
def searchcheque():
    if request.method == 'POST':
        cheque_no = int(request.form['chequeno'])
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM cms WHERE cheque_no = %s", (cheque_no,))
        cheque_results = cursor.fetchall()
        
        conn.close()
        return render_template(
            'cheque.html',
            cheque_results=cheque_results,
        )
    else:
        # For GET request, just show the empty search form
        return render_template('cheque.html', cheque_results=[])


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
