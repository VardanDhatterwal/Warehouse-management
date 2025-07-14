
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import os, random, sqlite3
from email_utils import send_email
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = 'warehouse_secret_key'
os.makedirs("static/barcodes", exist_ok=True)

products = []
reserved_stock = {}

# -- Initialize SQLite for orders
def init_order_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            customer_name TEXT,
            email TEXT,
            items TEXT,
            timestamp TEXT,
            status TEXT,
            status_updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
def init_user_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_order_db()

# -- Generate Order ID
def generate_order_id():
    return f"ORD-{random.randint(100000, 999999)}"

@app.route('/')
def root():
    return redirect('/login')

@app.route('/home')
def home():
    if session.get('role') == 'admin':
        return render_template('admin_dashboard.html', products=products)
    elif session.get('role') == 'customer':
        return render_template('customer_home.html', products=products)
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to DB
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        # Validate password
        if user and password == user[0]:
            session['email'] = email
            session['role'] = user[1]
            session['cart'] = {}
            flash(f'Logged in as {user[1]}', 'success')
            return redirect('/home')
        else:
            flash('Invalid email or password.', 'error')
            return redirect('/login')

    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        
        if email == 'vardan.kumar@innovasolutions.com':  
            role = 'admin'
        else:
            role = 'customer'

        
        session['email'] = email
        session['role'] = role
        session['cart'] = {}

        flash(f'Account created successfully as {role}.', 'success')
        return redirect('/home')

    return render_template('register.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("You’ve been logged out.", "info")
    return redirect('/login')

@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        order_id = request.form['order_id']
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        conn.close()

        if row:
            order = {
                'orderId': row[0],
                'customerName': row[1],
                'items': eval(row[2]),
                'timestamp': row[3],
                'status': row[4]
            }
            return render_template('track.html', order=order)
        else:
            flash('Order ID not found.', 'error')
    return render_template('track.html')

@app.route('/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return redirect('/login')

    name = request.form['name']
    warehouse = request.form['warehouse']
    cabin = request.form['cabin']
    tray = request.form['tray']
    price = request.form['price']
    image = request.files['image']

    if name and warehouse and cabin and tray and image and price:
        try:
            price = float(price)  # Ensure it's a valid number
        except ValueError:
            flash('Invalid price value.', 'error')
            return redirect('/home')

        product_id = products[-1]['id'] + 1 if products else 1

        # Save image
        os.makedirs("static/images", exist_ok=True)
        image_filename = f"product_{product_id}_{image.filename}"
        image_path = os.path.join("static", "images", image_filename)
        image.save(image_path)

        # Generate barcode
        barcode_filename = f"product_{product_id}"
        barcode_path = os.path.join("static", "barcodes", barcode_filename)
        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.4,
            "module_height": 20,
            "quiet_zone": 6.5,
            "font_size": 10,
            "text_distance": 1,
            "write_text": True,
            "dpi": 300
        })
        Code128(str(product_id), writer=writer).save(barcode_path)

        products.append({
            'id': product_id,
            'name': name,
            'warehouse': warehouse,
            'cabin': cabin,
            'tray': tray,
            'price': price,
            'barcode': f"barcodes/{barcode_filename}.png",
            'image': f"images/{image_filename}"
        })

        flash('✅ Product added with image, barcode, and price!', 'success')
    else:
        flash('Please fill all fields.', 'error')

    return redirect('/home')


@app.route('/delete-product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        return redirect('/login')

    global products
    products = [p for p in products if p['id'] != pid]
    reserved_stock.pop(pid, None)
    flash('Product deleted.', 'info')
    return redirect('/home')

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if session.get('role') != 'customer':
        return redirect('/login')

    pid = int(request.form['product_id'])
    cart = session.get('cart', {})

    if str(pid) in cart:
        cart[str(pid)] += 1
    else:
        cart[str(pid)] = 1

    session['cart'] = cart
    flash('Added to cart!', 'success')
    return redirect('/home')

@app.route('/cart')
def cart_page():
    if session.get('role') != 'customer':
        return redirect('/login')

    cart = session.get('cart', {})
    cart_items = []
    total = 0

    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = next((p for p in products if p['id'] == pid), None)
        if product:
            item_total = qty * product['price']
            cart_items.append({
                'id': pid,
                'name': product['name'],
                'quantity': qty,
                'price': product['price'],         # ✅ Include this!
                'total': item_total                # ✅ And this
            })
            total += item_total

    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/checkout', methods=['POST'])
def checkout():
    if session.get('role') != 'customer':
        return redirect('/login')

    customer_name = request.form['customer_name']
    email = session.get('email')

    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect('/cart')

    order_items = []
    now = datetime.now()
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        qty = int(qty)
        product = next((p for p in products if p['id'] == pid), None)
        if product:
            order_items.append({'productId': pid, 'quantity': qty, 'name': product['name']})
            reserved_stock[pid] = now

    order_id = generate_order_id()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (order_id, customer_name, email, items, timestamp, status, status_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        order_id,
        customer_name,
        email,
        str(order_items),
        timestamp,
        'Processing',
        now.strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    conn.close()

    # ✅ Send confirmation email
    from email_utils import send_email
    send_email({
        'orderId': order_id,
        'customerName': customer_name,
        'email': email,
        'items': order_items,
        'timestamp': timestamp,
        'status': 'Processing'
    })

    session.pop('cart', None)
    flash('Order placed successfully! Confirmation email sent.', 'success')
    return redirect('/home')


@app.route('/history')
def order_history():
    if session.get('role') != 'customer':
        return redirect('/login')

    email = session.get('email')
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders WHERE email = ?", (email,))
    rows = c.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            'orderId': row[0],
            'customerName': row[1],
            'items': eval(row[2]),
            'timestamp': row[3],
            'status': row[4]
        })

    return render_template('order_history.html', orders=history)

# -- Default Products
if not products:
    default_items = [
    {'name': 'Laptop', 'warehouse': 'Delhi', 'cabin': 'A1', 'tray': 'T1', 'price': 55000},
    {'name': 'Headphones', 'warehouse': 'Mumbai', 'cabin': 'B2', 'tray': 'T3', 'price': 1500},
    {'name': 'Camera', 'warehouse': 'Bangalore', 'cabin': 'C3', 'tray': 'T5', 'price': 35000},
    {'name': 'Smartphone', 'warehouse': 'Chennai', 'cabin': 'D1', 'tray': 'T7', 'price': 20000},
    {'name': 'Keyboard', 'warehouse': 'Hyderabad', 'cabin': 'E4', 'tray': 'T2', 'price': 999}
]

    for i, item in enumerate(default_items, start=1):
        barcode_filename = f"product_{i}"
        barcode_path = os.path.join("static", "barcodes", barcode_filename)

        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.4,
            "module_height": 20,
            "quiet_zone": 6.5,
            "font_size": 10,
            "text_distance": 1,
            "write_text": True,
            "dpi": 300
        })
        Code128(str(i), writer=writer).save(barcode_path)
        products.append({
        'id': i,
    'name': item['name'],
    'warehouse': item['warehouse'],
    'cabin': item['cabin'],
    'tray': item['tray'],
    'price': item['price'],  # ✅ Add this
    'barcode': f"barcodes/{barcode_filename}.png"
})

@app.route('/manage-orders', methods=['GET', 'POST'])
def manage_orders():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    if request.method == 'POST':
        order_id = request.form['order_id']
        new_status = request.form['status']
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update the status in DB
        c.execute("UPDATE orders SET status = ?, status_updated_at = ? WHERE order_id = ?", (new_status, updated_at, order_id))
        conn.commit()

        # Send email if status is delivered
        if new_status == "Delivered":
            c.execute("SELECT customer_name, email, items, timestamp FROM orders WHERE order_id = ?", (order_id,))
            row = c.fetchone()
            if row:
                order = {
                    "orderId": order_id,
                    "customerName": row[0],
                    "email": row[1],
                    "items": eval(row[2]),
                    "timestamp": row[3]
                }
                send_email(order, delivered=True)

        flash(f"Order {order_id} status updated to {new_status}", "success")
        return redirect('/manage-orders')

    # Show all orders
    c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders ORDER BY id DESC")
    orders = c.fetchall()
    conn.close()

    order_list = []
    for o in orders:
        order_list.append({
            "orderId": o[0],
            "customerName": o[1],
            "items": eval(o[2]),
            "timestamp": o[3],
            "status": o[4]
        })

    return render_template('manage_orders.html', orders=order_list)


if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
import os, random, sqlite3
from email_utils import send_email
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = 'warehouse_secret_key'
os.makedirs("static/barcodes", exist_ok=True)

products = []
reserved_stock = {}

# -- Initialize SQLite for orders
def init_order_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            customer_name TEXT,
            email TEXT,
            items TEXT,
            timestamp TEXT,
            status TEXT,
            status_updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_order_db()

# -- Generate Order ID
def generate_order_id():
    return f"ORD-{random.randint(100000, 999999)}"

@app.route('/')
def root():
    return redirect('/login')

@app.route('/home')
def home():
    if session.get('role') == 'admin':
        return render_template('admin_dashboard.html', products=products)
    elif session.get('role') == 'customer':
        return render_template('customer_home.html', products=products)
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        session['email'] = email
        session['role'] = role
        session['cart'] = {}
        flash(f"Logged in as {role}", 'success')
        return redirect('/home')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        session['email'] = email
        session['role'] = role
        session['cart'] = {}
        flash('Account created successfully.', 'success')
        return redirect('/home')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You’ve been logged out.", "info")
    return redirect('/login')

@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        order_id = request.form['order_id']
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        conn.close()

        if row:
            order = {
                'orderId': row[0],
                'customerName': row[1],
                'items': eval(row[2]),
                'timestamp': row[3],
                'status': row[4]
            }
            return render_template('track.html', order=order)
        else:
            flash('Order ID not found.', 'error')
    return render_template('track.html')

@app.route('/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return redirect('/login')

    name = request.form['name']
    warehouse = request.form['warehouse']
    cabin = request.form['cabin']
    tray = request.form['tray']
    price = request.form['price']
    image = request.files['image']

    if name and warehouse and cabin and tray and image and price:
        try:
            price = float(price)  # Ensure it's a valid number
        except ValueError:
            flash('Invalid price value.', 'error')
            return redirect('/home')

        product_id = products[-1]['id'] + 1 if products else 1

        # Save image
        os.makedirs("static/images", exist_ok=True)
        image_filename = f"product_{product_id}_{image.filename}"
        image_path = os.path.join("static", "images", image_filename)
        image.save(image_path)

        # Generate barcode
        barcode_filename = f"product_{product_id}"
        barcode_path = os.path.join("static", "barcodes", barcode_filename)
        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.4,
            "module_height": 20,
            "quiet_zone": 6.5,
            "font_size": 10,
            "text_distance": 1,
            "write_text": True,
            "dpi": 300
        })
        Code128(str(product_id), writer=writer).save(barcode_path)

        products.append({
            'id': product_id,
            'name': name,
            'warehouse': warehouse,
            'cabin': cabin,
            'tray': tray,
            'price': price,
            'barcode': f"barcodes/{barcode_filename}.png",
            'image': f"images/{image_filename}"
        })

        flash('✅ Product added with image, barcode, and price!', 'success')
    else:
        flash('Please fill all fields.', 'error')

    return redirect('/home')


@app.route('/delete-product/<int:pid>')
def delete_product(pid):
    if session.get('role') != 'admin':
        return redirect('/login')

    global products
    products = [p for p in products if p['id'] != pid]
    reserved_stock.pop(pid, None)
    flash('Product deleted.', 'info')
    return redirect('/home')

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if session.get('role') != 'customer':
        return redirect('/login')

    pid = int(request.form['product_id'])
    cart = session.get('cart', {})

    if str(pid) in cart:
        cart[str(pid)] += 1
    else:
        cart[str(pid)] = 1

    session['cart'] = cart
    flash('Added to cart!', 'success')
    return redirect('/home')

@app.route('/cart')
def cart_page():
    if session.get('role') != 'customer':
        return redirect('/login')

    cart = session.get('cart', {})
    cart_items = []
    total = 0

    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = next((p for p in products if p['id'] == pid), None)
        if product:
            item_total = qty * product['price']
            cart_items.append({
                'id': pid,
                'name': product['name'],
                'quantity': qty,
                'price': product['price'],         # ✅ Include this!
                'total': item_total                # ✅ And this
            })
            total += item_total

    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/checkout', methods=['POST'])
def checkout():
    if session.get('role') != 'customer':
        return redirect('/login')

    customer_name = request.form['customer_name']
    email = session.get('email')

    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'error')
        return redirect('/cart')

    order_items = []
    now = datetime.now()
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        qty = int(qty)
        product = next((p for p in products if p['id'] == pid), None)
        if product:
            order_items.append({'productId': pid, 'quantity': qty, 'name': product['name']})
            reserved_stock[pid] = now

    order_id = generate_order_id()
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (order_id, customer_name, email, items, timestamp, status, status_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        order_id,
        customer_name,
        email,
        str(order_items),
        timestamp,
        'Processing',
        now.strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    conn.close()

    # ✅ Send confirmation email
    from email_utils import send_email
    send_email({
        'orderId': order_id,
        'customerName': customer_name,
        'email': email,
        'items': order_items,
        'timestamp': timestamp,
        'status': 'Processing'
    })

    session.pop('cart', None)
    flash('Order placed successfully! Confirmation email sent.', 'success')
    return redirect('/home')


@app.route('/history')
def order_history():
    if session.get('role') != 'customer':
        return redirect('/login')

    email = session.get('email')
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders WHERE email = ?", (email,))
    rows = c.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            'orderId': row[0],
            'customerName': row[1],
            'items': eval(row[2]),
            'timestamp': row[3],
            'status': row[4]
        })

    return render_template('order_history.html', orders=history)

# -- Default Products
if not products:
    default_items = [
    {'name': 'Laptop', 'warehouse': 'Delhi', 'cabin': 'A1', 'tray': 'T1', 'price': 55000},
    {'name': 'Headphones', 'warehouse': 'Mumbai', 'cabin': 'B2', 'tray': 'T3', 'price': 1500},
    {'name': 'Camera', 'warehouse': 'Bangalore', 'cabin': 'C3', 'tray': 'T5', 'price': 35000},
    {'name': 'Smartphone', 'warehouse': 'Chennai', 'cabin': 'D1', 'tray': 'T7', 'price': 20000},
    {'name': 'Keyboard', 'warehouse': 'Hyderabad', 'cabin': 'E4', 'tray': 'T2', 'price': 999}
]

    for i, item in enumerate(default_items, start=1):
        barcode_filename = f"product_{i}"
        barcode_path = os.path.join("static", "barcodes", barcode_filename)

        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.4,
            "module_height": 20,
            "quiet_zone": 6.5,
            "font_size": 10,
            "text_distance": 1,
            "write_text": True,
            "dpi": 300
        })
        Code128(str(i), writer=writer).save(barcode_path)
        products.append({
        'id': i,
    'name': item['name'],
    'warehouse': item['warehouse'],
    'cabin': item['cabin'],
    'tray': item['tray'],
    'price': item['price'],  # ✅ Add this
    'barcode': f"barcodes/{barcode_filename}.png"
})

@app.route('/manage-orders', methods=['GET', 'POST'])
def manage_orders():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('orders.db')
    c = conn.cursor()

    if request.method == 'POST':
        order_id = request.form['order_id']
        new_status = request.form['status']
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update the status in DB
        c.execute("UPDATE orders SET status = ?, status_updated_at = ? WHERE order_id = ?", (new_status, updated_at, order_id))
        conn.commit()

        # Send email if status is delivered
        if new_status == "Delivered":
            c.execute("SELECT customer_name, email, items, timestamp FROM orders WHERE order_id = ?", (order_id,))
            row = c.fetchone()
            if row:
                order = {
                    "orderId": order_id,
                    "customerName": row[0],
                    "email": row[1],
                    "items": eval(row[2]),
                    "timestamp": row[3]
                }
                send_email(order, delivered=True)

        flash(f"Order {order_id} status updated to {new_status}", "success")
        return redirect('/manage-orders')

    # Show all orders
    c.execute("SELECT order_id, customer_name, items, timestamp, status FROM orders ORDER BY id DESC")
    orders = c.fetchall()
    conn.close()

    order_list = []
    for o in orders:
        order_list.append({
            "orderId": o[0],
            "customerName": o[1],
            "items": eval(o[2]),
            "timestamp": o[3],
            "status": o[4]
        })

    return render_template('manage_orders.html', orders=order_list)


if __name__ == '__main__':
    app.run(debug=True)
