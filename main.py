#all imports
import sqlite3, os, uuid
from flask import Flask, render_template, request, session, redirect, url_for, g, make_response
from datetime import datetime
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# config for image file uploading
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


# making database connection
def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect('grocery_store.db')
  return db


@app.teardown_appcontext
def close_db(error):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()


# initializing database and admin detail inserting
def initialize_database():
  with app.app_context():
    db = get_db()
    cursor = db.cursor()

    # creating the users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        is_admin INTEGER DEFAULT 0
                        )''')

    # creating the Sections table for categories
    cursor.execute('''CREATE TABLE IF NOT EXISTS sections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        image TEXT
                        )''')
    # creating the products table for products in specific categories
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        manufacture_date DATE NULL,
                        expiry_date DATE NULL,
                        price REAL NOT NULL,
                        unit TEXT NOT NULL,
                        available_quantity INTEGER NOT NULL,
                        section_id INTEGER,
                        image TEXT,
                        FOREIGN KEY (section_id) REFERENCES sections (id)
                        )''')
    # creating the user_cart table for products in users cart
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_cart (
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (product_id) REFERENCES products (id),
                        PRIMARY KEY (user_id, product_id)
                        )''')
    # creating the shopping_history table for users shopping history
    cursor.execute('''CREATE TABLE IF NOT EXISTS shopping_history (
                        order_id TEXT,
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER,
                        purchase_date TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (product_id) REFERENCES products (id)
                        )''')

    # Added admin details
    cursor.execute(
      '''INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)''',
      ('navjot', 'password', 1))

    db.commit()


@app.before_request
def before_request():
  initialize_database()


def allowed_file(filename):
  return '.' in filename and filename.rsplit(
    '.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']




# ensures that all routes in the app will return the appropriate CORS headers.

def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

@app.after_request
def after_request(response):
    if request.method == 'OPTIONS':
        return add_cors_headers(make_response())
    return add_cors_headers(response)


# Homepage
@app.route('/')
def home():
  return render_template('index.html')


# user login page
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    # fetch the user from the database based on the username and password
    cursor = get_db().cursor()
    cursor.execute(
      '''SELECT * FROM users WHERE username=? AND password=? AND is_admin=?''',
      (username, password, 0))
    user = cursor.fetchone()

    if user:
      session['user_id'] = user[0]
      return redirect(url_for('user_dashboard'))
    else:
      # user not found, display login page with an error message
      return render_template('login.html',
                             error_message="Invalid username or password")

  return render_template('login.html')


# user signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']

    # checking if the username already exists in the database
    cursor = get_db().cursor()
    cursor.execute('''SELECT * FROM users WHERE username=?''', (username, ))
    existing_user = cursor.fetchone()

    if existing_user:
      # Username already exists, display error message on the signup page
      return render_template(
        'signup.html',
        error_message=
        "Username already exists. Please choose a different username.")

    # inserting new user into the database
    cursor.execute('''INSERT INTO users (username, password) VALUES (?, ?)''',
                   (username, password))
    get_db().commit()

    return render_template('signup.html',
                           success_message="Account created successfully!")

  return render_template('signup.html')


# admin login page
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    # fetching the admin from the database based on the username and password
    cursor = get_db().cursor()
    cursor.execute(
      '''SELECT * FROM users WHERE username=? AND password=? AND is_admin=?''',
      (username, password, 1))
    admin = cursor.fetchone()

    if admin:
      session['admin_id'] = admin[0]
      return redirect(url_for('admin_dashboard'))
    else:
      return render_template('admin_login.html',
                             error_message="Invalid username or password")

  return render_template('admin_login.html')


# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
  if 'admin_id' in session:
    # fetch sections and products
    cursor = get_db().cursor()
    sections = cursor.execute("SELECT id, name FROM sections").fetchall()
    products = cursor.execute(
      "SELECT id, name, price, unit, available_quantity, section_id FROM products"
    ).fetchall()

    # converting results to a list of dictionaries
    sections_list = [{
      'id': section[0],
      'name': section[1]
    } for section in sections]
    products_list = [{
      'id': product[0],
      'name': product[1],
      'price': product[2],
      'unit': product[3],
      'available_quantity': product[4],
      'section_id': product[5]
    } for product in products]

    # passing the data to the template context
    return render_template('admin_dashboard.html',
                           sections=sections_list,
                           products=products_list)

  return redirect(url_for('admin_login'))


# Category Management - new section/category page
@app.route('/admin/add_category', methods=['GET', 'POST'])
def add_category():
  if 'admin_id' in session:
    if request.method == 'POST':
      name = request.form['name']
      image = request.files['image']

      cursor = get_db().cursor()
      cursor.execute("SELECT id FROM sections WHERE name=?", (name, ))
      existing_category = cursor.fetchone()
      # checking if the cateogery already exists in the database
      if existing_category:
        return render_template(
          'add_category.html',
          error_message=f"A category with the name '{name}' already exists.")
      # for uploading category image
      if image and allowed_file(image.filename):
        filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      else:
        return render_template('add_category.html',
                               error_message="image extension not allowed")
      # inserting new section category into the database
      cursor = get_db().cursor()
      cursor.execute('''INSERT INTO sections (name, image) VALUES (?, ?)''',
                     (name, filename))
      get_db().commit()

      return redirect(url_for('admin_dashboard'))

    return render_template('add_category.html')

  return redirect(url_for('admin_login'))


# Category Management - Edit section/category page
@app.route('/admin/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
  if 'admin_id' in session:
    # Fetch the category from the database using the category_id
    cursor = get_db().cursor()
    cursor.execute("SELECT name, image FROM sections WHERE id=?",
                   (category_id, ))
    category = cursor.fetchone()

    if request.method == 'POST':
      name = request.form['name']
      image = request.files['image']

      # Check if the user uploaded a new image
      if image:
        if allowed_file(image.filename):
          # Delete the previous image
          if category[1]:
            previous_image_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                               category[1])
            if os.path.exists(previous_image_path):
              os.remove(previous_image_path)

          # Save the new image
          filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]
          image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
          return render_template('edit_category.html',
                                 category=category,
                                 error_message="Image extension not allowed.")
      else:
        filename = category[1]

      # Check if the new name is unique among categories
      cursor.execute("SELECT id FROM sections WHERE name=? AND id<>?",
                     (name, category_id))
      existing_category = cursor.fetchone()

      if existing_category:
        return render_template(
          'edit_category.html',
          category=category,
          error_message="A category with the same name already exists.")

      # Update the category in the database
      cursor.execute("UPDATE sections SET name=?, image=? WHERE id=?",
                     (name, filename, category_id))
      get_db().commit()

      # Redirect to the admin dashboard
      return redirect(url_for('admin_dashboard'))

    return render_template('edit_category.html', category=category)

  return render_template('admin_login.html')


# Category Management - Remove a section/category
@app.route('/admin/remove_category/<int:category_id>', methods=['GET', 'POST'])
def remove_category(category_id):
  if 'admin_id' in session:
    # Fetch the category from the database using the category_id
    cursor = get_db().cursor()
    cursor.execute("SELECT name, image FROM sections WHERE id=?",
                   (category_id, ))
    category = cursor.fetchone()

    cursor.execute("SELECT image FROM products WHERE section_id=?",
                   (category_id, ))
    product_images = cursor.fetchall()

    if request.method == 'POST':
      # Remove the category from the database
      cursor.execute("DELETE FROM sections WHERE id=?", (category_id, ))
      cursor.execute("DELETE FROM products WHERE section_id=?",
                     (category_id, ))
      get_db().commit()

      # Delete the images of sections associated with the deleted category
      if category[1]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], category[1])
        if os.path.exists(image_path):
          os.remove(image_path)

      # Delete the images of products associated with the deleted category

      for product_image in product_images:
        if product_image[0]:
          product_image_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                            product_image[0])
          if os.path.exists(product_image_path):
            os.remove(product_image_path)

      return redirect(url_for('admin_dashboard'))

    return render_template('remove_category.html', category_name=category[0])

  return render_template('admin_login.html')


# Product Management - Create a new product
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
  if 'admin_id' in session:

    cursor = get_db().cursor()
    sections = cursor.execute("SELECT id, name FROM sections").fetchall()

    if request.method == 'POST':
      name = request.form['name']
      manufacture_date = request.form['manufacture_date']
      expiry_date = request.form['expiry_date']
      price = request.form['price']
      unit = request.form['unit']
      available_quantity = request.form['available_quantity']
      section_id = request.form['section_id']
      image = request.files['image']
      cursor = get_db().cursor()
      cursor.execute("SELECT id FROM products WHERE name=?", (name, ))
      existing_product = cursor.fetchone()

      if existing_product:
        return render_template(
          'add_product.html',
          error_message=f"A product with the name '{name}' already exists.",
          sections=sections)

      if image and allowed_file(image.filename):
        filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
      else:
        return render_template('add_product.html',
                               error_message="image extension not allowed",
                               sections=sections)

      cursor = get_db().cursor()
      cursor.execute(
        '''INSERT INTO products (name, manufacture_date, expiry_date, price, unit, available_quantity, section_id, image) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (name, manufacture_date, expiry_date, price, unit, available_quantity,
         section_id, filename))
      get_db().commit()

      return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html', sections=sections)

  return render_template('admin_login.html')


# Product Management - Edit a product
@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
  if 'admin_id' in session:
    cursor = get_db().cursor()
    product = cursor.execute('''SELECT * FROM products WHERE id=?''',
                             (product_id, )).fetchone()
    sections = cursor.execute("SELECT id, name FROM sections").fetchall()

    if request.method == 'POST':
      # Get form data
      name = request.form['name']
      manufacture_date = request.form['manufacture_date']
      expiry_date = request.form['expiry_date']
      price = request.form['price']
      unit = request.form['unit']
      available_quantity = request.form['available_quantity']
      section_id = request.form['section_id']
      image = request.files['image']

      # Checking if the user uploaded a new image
      if image:
        if allowed_file(image.filename):
          # Delete the previous image
          if product[8]:
            previous_image_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                               product[8])
            if os.path.exists(previous_image_path):
              os.remove(previous_image_path)

          # Save the new image
          filename = str(uuid.uuid4()) + os.path.splitext(image.filename)[1]
          image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
          return render_template('edit_product.html',
                                 product=product,
                                 sections=sections,
                                 error_message="Image extension not allowed.")
      else:
        filename = product[8]

      # Checking if the new name is unique among products
      cursor.execute("SELECT id FROM products WHERE name=? AND id<>?",
                     (name, product_id))
      existing_product = cursor.fetchone()

      if existing_product:
        return render_template(
          'edit_product.html',
          product=product,
          sections=sections,
          error_message="A product with the same name already exists.")

      # Update the product in the database
      cursor.execute(
        '''
                    UPDATE products SET
                    name=?, manufacture_date=?, expiry_date=?, price=?, unit=?,
                    available_quantity=?, section_id=?, image=?
                    WHERE id=?
                ''', (name, manufacture_date, expiry_date, price, unit,
                      available_quantity, section_id, filename, product_id))
      get_db().commit()

      # Redirect to the admin dashboard
      return redirect(url_for('admin_dashboard'))

    return render_template('edit_product.html',
                           product=product,
                           sections=sections)

  return render_template('admin_login.html')


# Product Management - Remove a product
@app.route('/admin/remove_product/<int:product_id>', methods=['GET', 'POST'])
def remove_product(product_id):
  if 'admin_id' in session:
    cursor = get_db().cursor()
    cursor.execute('''SELECT name, image FROM products WHERE id=?''',
                   (product_id, ))
    product = cursor.fetchone()

    if request.method == 'POST':
      # Remove the product from the database
      cursor.execute('''DELETE FROM products WHERE id=?''', (product_id, ))
      get_db().commit()

      if product[1]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product[1])
        if os.path.exists(image_path):
          os.remove(image_path)

      # Redirect to the admin dashboard
      return redirect(url_for('admin_dashboard'))

    return render_template('remove_product.html', product=product[0])

  return render_template('admin_login.html')


# Functions for showing graphs in insights page
def fetch_most_sold_products():
  cursor = get_db().cursor()
  most_sold_query = '''
        SELECT p.name, SUM(sh.quantity) AS total_sold
        FROM products p
        JOIN shopping_history sh ON p.id = sh.product_id
        GROUP BY p.id
        ORDER BY total_sold DESC
        LIMIT 5
    '''
  most_sold_products = cursor.execute(most_sold_query).fetchall()
  return most_sold_products


def fetch_registered_users_count():
  cursor = get_db().cursor()
  registered_users_query = '''
        SELECT COUNT(*) FROM users WHERE is_admin = 0
    '''
  registered_users_count = cursor.execute(registered_users_query).fetchone()[0]
  return registered_users_count


def fetch_low_quantity_products():
  cursor = get_db().cursor()
  low_quantity_query = '''
        SELECT name, available_quantity
        FROM products
        WHERE available_quantity <= 10
    '''
  low_quantity_products = cursor.execute(low_quantity_query).fetchall()
  return low_quantity_products


#Route to show the graphs and details in insight page
@app.route('/admin/insights')
def admin_insights():
  if 'admin_id' in session:
    most_sold_products = fetch_most_sold_products()
    registered_users_count = fetch_registered_users_count()
    low_quantity_products = fetch_low_quantity_products()

    # Generate the Most Sold Products Bar Chart
    plt.figure(figsize=(8, 6))
    products = [product[0] for product in most_sold_products]
    quantities = [product[1] for product in most_sold_products]
    plt.bar(products, quantities)
    plt.xlabel('Products')
    plt.ylabel('Quantity Sold')
    plt.title('Most Sold Products')
    most_sold_chart_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                        'most_sold_chart.png')
    plt.savefig(most_sold_chart_path)
    plt.clf()  # Clear the current figure

    return render_template('admin_insights.html',
                           most_sold_chart=most_sold_chart_path,
                           registered_users_count=registered_users_count,
                           low_quantity_products=low_quantity_products)

  return redirect(url_for('admin_login'))


# Function to fetch user's cart items
def fetch_user_cart(user_id):
  cursor = get_db().cursor()
  cursor.execute(
    '''SELECT p.id, p.name, p.price, p.unit, p.available_quantity, c.quantity
            FROM products AS p
            JOIN user_cart AS c ON p.id = c.product_id
            WHERE c.user_id=?''', (user_id, ))
  cart_items = cursor.fetchall()
  return cart_items


# Function to get the cart item for a product
def get_cart_item(user_id, product_id):
  cursor = get_db().cursor()
  cursor.execute("SELECT * FROM user_cart WHERE user_id=? AND product_id=?",
                 (user_id, product_id))
  cart_item = cursor.fetchone()
  return cart_item


# Function to update a cart item's quantity
def update_cart_item(user_id, product_id, quantity):
  cursor = get_db().cursor()
  cursor.execute(
    "UPDATE user_cart SET quantity=? WHERE user_id=? AND product_id=?",
    (quantity, user_id, product_id))
  get_db().commit()


# Route to update a cart item's quantity
@app.route('/update_cart_item', methods=['POST'])
def update_cart_item_route():
  if 'user_id' in session:
    user_id = session['user_id']
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])

    if quantity >= 0:
      cursor = get_db().cursor()
      if quantity == 0:
        cursor.execute(
          "DELETE FROM user_cart WHERE user_id=? AND product_id=?",
          (user_id, product_id))
      else:
        cursor.execute(
          "UPDATE user_cart SET quantity=? WHERE user_id=? AND product_id=?",
          (quantity, user_id, product_id))
      get_db().commit()

  return redirect(url_for('user_dashboard'))


def get_cart_items(user_id):
  cursor = get_db().cursor()
  cart_items = cursor.execute(
    "SELECT product_id, quantity FROM user_cart WHERE user_id = ?",
    (user_id, )).fetchall()
  return cart_items


# Function to get the quantity of a product in the user's cart
def get_cart_quantity(product_id, user_cartt):
  for cart_item in user_cartt:
    if cart_item[1] == product_id:
      return cart_item[2]
  return 0


# route for User dashboard
@app.route('/user/dashboard', methods=['GET', 'POST'])
def user_dashboard():
  if 'user_id' in session:
    user_id = session['user_id']
    cursor = get_db().cursor()
    current_user = cursor.execute('''SELECT * FROM users WHERE id=?''',
                                  (user_id, )).fetchone()
    sections = cursor.execute("SELECT * FROM sections").fetchall()

    products_by_section = {}
    for section in sections:
      section_id = section[0]
      cursor.execute("SELECT * FROM products WHERE section_id=?",
                     (section_id, ))
      products = cursor.fetchall()
      products_by_section[section_id] = products

    user_cartt = cursor.execute("SELECT * FROM user_cart WHERE user_id=?",
                                (user_id, )).fetchall()

    return render_template('user_dashboard.html',
                           current_user=current_user,
                           sections=sections,
                           products_by_section=products_by_section,
                           user_cartt=user_cartt,
                           get_cart_quantity=get_cart_quantity)

  return redirect(url_for('login'))


# route for search page
@app.route('/user/search', methods=['GET', 'POST'])
def search():
  if 'user_id' in session:
    user_id = session['user_id']

    if request.method == 'POST':
      search_query = request.form.get('search_query')
      section_results = []
      cursor = get_db().cursor()

      # Search by category name
      cursor.execute("SELECT * FROM sections WHERE name LIKE ?",
                     ('%' + search_query + '%', ))
      sections = cursor.fetchall()

      for section in sections:
        section_id, section_name, section_image = section
        cursor.execute("SELECT * FROM products WHERE section_id = ?",
                       (section_id, ))
        products_in_section = cursor.fetchall()
        if products_in_section:
          section_results.append((section_name, products_in_section))

      # Search by product name or price
      product_results = []
      try:
        min_price = float(search_query)
        cursor.execute("SELECT * FROM products WHERE price >= ?",
                       (min_price, ))
        product_results = cursor.fetchall()
      except ValueError:
        cursor.execute("SELECT * FROM products WHERE name LIKE ?",
                       ('%' + search_query + '%', ))
        product_results = cursor.fetchall()

      user_cartt = cursor.execute("SELECT * FROM user_cart WHERE user_id=?",
                                  (user_id, )).fetchall()
      return render_template('search.html',
                             section_results=section_results,
                             product_results=product_results,
                             get_cart_quantity=get_cart_quantity,
                             user_cartt=user_cartt,
                             search_query=search_query)

    return render_template('search.html',
                           section_results=[],
                           product_results=[])

  return redirect(url_for('login'))


# User cart
@app.route('/user/cart', methods=['GET'])
def user_cart():
  if 'user_id' in session:
    user_id = session['user_id']
    cursor = get_db().cursor()

    # Retrieve cart items for the user from the database
    cart = '''
            SELECT products.*, user_cart.quantity
            FROM products
            JOIN user_cart ON products.id = user_cart.product_id
            WHERE user_cart.user_id = ?
        '''
    user_cart = cursor.execute(cart, (user_id, )).fetchall()

    product_total = (item[4] * item[9] for item in user_cart)
    # Calculate total price
    cart_total = sum(item[4] * item[9] for item in user_cart)

    user_cartt = cursor.execute("SELECT * FROM user_cart WHERE user_id=?",
                                (user_id, )).fetchall()

    return render_template('cart.html',
                           user_cart=user_cart,
                           product_total=product_total,
                           cart_total=cart_total,
                           get_cart_quantity=get_cart_quantity,
                           user_cartt=user_cartt)

  return redirect(url_for('login'))


# Route to add a product to the cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
  if 'user_id' in session:
    user_id = session['user_id']
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])

    # Fetch the user's cart from the database
    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM user_cart WHERE user_id=? AND product_id=?",
                   (user_id, product_id))
    cart_item = cursor.fetchone()

    # Check if the product is already in the cart
    if cart_item:
      cart_quantity = quantity
      cursor.execute(
        "UPDATE user_cart SET quantity=? WHERE user_id=? AND product_id=?",
        (cart_quantity, user_id, product_id))
    else:
      cursor.execute(
        "INSERT INTO user_cart (user_id, product_id, quantity) VALUES (?, ?, ?)",
        (user_id, product_id, quantity))

    get_db().commit()

    return redirect(request.referrer or url_for('user_dashboard'))

  return redirect(url_for('login'))


# remove item from cart
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
  if 'user_id' in session:
    user_id = session['user_id']
    product_id = int(request.form['product_id'])
    cursor = get_db().cursor()

    # Remove the item from the user's cart in the database
    cursor.execute('DELETE FROM user_cart WHERE user_id=? AND product_id=?',
                   (user_id, product_id))
    get_db().commit()

    return redirect(request.referrer or url_for('user_dashboard'))

  return redirect(url_for('login'))


# Functions needed during checkout


def remove_cart_item(user_id, product_id):
  cursor = get_db().cursor()
  cursor.execute("DELETE FROM user_cart WHERE user_id=? AND product_id=?",
                 (user_id, product_id))
  get_db().commit()


def update_product_available_quantity(product_id, new_available_quantity):
  cursor = get_db().cursor()
  cursor.execute("UPDATE products SET available_quantity=? WHERE id=?",
                 (new_available_quantity, product_id))
  get_db().commit()


# Function for inserting shop gistory data after succesful checkout
def create_shopping_history(user_id, user_cart):
  cursor = get_db().cursor()
  purchase_date = datetime.now().strftime('%m-%d-%Y %H:%M')

  order_id = str(uuid.uuid4())
  print(order_id)
  for cart_item in user_cart:
    product_id = cart_item[0]
    quantity = cart_item[5]
    cursor.execute(
      "INSERT INTO shopping_history (order_id, user_id, product_id, quantity, purchase_date) VALUES (?, ?, ?, ?, ?)",
      (order_id, user_id, product_id, quantity, purchase_date))

  get_db().commit()


# for clearing user's cart
def clear_user_cart(user_id):
  cursor = get_db().cursor()
  cursor.execute("DELETE FROM user_cart WHERE user_id=?", (user_id, ))
  get_db().commit()


# route for checkout button
@app.route('/user/checkout', methods=['POST'])
def checkout():
  if 'user_id' in session:
    user_id = session['user_id']
    user_cart = fetch_user_cart(user_id)  # Fetch user's cart items

    for cart_item in user_cart:
      product_id = cart_item[0]
      requested_quantity = cart_item[5]
      available_quantity = cart_item[4]

      if requested_quantity > available_quantity:
        remove_cart_item(user_id, product_id)  # Remove the product from cart
        return redirect(url_for('user_cart'))

      if available_quantity == 0:
        remove_cart_item(user_id, product_id)  # Remove the product from cart
        return redirect(url_for('user_cart'))

      new_available_quantity = available_quantity - requested_quantity
      update_product_available_quantity(product_id, new_available_quantity)

    create_shopping_history(user_id,
                            user_cart)  # Create shopping history entry
    clear_user_cart(user_id)  # Clear user's cart

    return redirect(url_for('thanks'))

  return redirect(url_for('login'))


# route for thanks page
@app.route('/user/thanks')
def thanks():
  if 'user_id' in session:
    return render_template('thanks.html')

  return redirect(url_for('login'))


# fetching purchase history
def fetch_purchase_history(user_id):
  cursor = get_db().cursor()
  history_query = '''
        SELECT shopping_history.order_id,
               shopping_history.purchase_date,
               products.name,
               shopping_history.quantity,
               products.price, products.unit
        FROM shopping_history
        JOIN products ON shopping_history.product_id = products.id
        WHERE shopping_history.user_id = ?
    '''
  user_history = cursor.execute(history_query, (user_id, )).fetchall()

  return user_history


# Route to show user's history
@app.route('/user/history')
def purchase_history():
  if 'user_id' in session:
    user_id = session['user_id']
    user_history = fetch_purchase_history(user_id)

    # Organize user_history by order_id
    order_history = {}
    for row in user_history:
      order_id = row[0]
      if order_id not in order_history:
        order_history[order_id] = []
      order_history[order_id].append(row)

    # Calculate order_total for each order
    for order_id, items in order_history.items():
      order_total = sum(item[3] * item[4] for item in items)
      order_history[order_id] = (order_history[order_id], order_total)

    return render_template('purchase_history.html',
                           order_history=order_history)

  return redirect(url_for('login'))


def user_logout():
  if 'user_id' in session:
    session.pop('user_id', None)
  return redirect(url_for('login'))


@app.route('/admin/logout')
def admin_logout():
  if 'admin_id' in session:
    session.pop('admin_id', None)
  return redirect(url_for('admin_login'))


if __name__ == '__main__':
  app.run(port=5050)
