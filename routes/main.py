from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify, send_file
from models import db, Product, Category, User, Review, Coupon, Order, OrderItem, PasswordResetToken
from config import UPLOADS_DIR
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy import text
import secrets, os, requests

main_bp = Blueprint('main', __name__)


def get_cart():
    return session.get('cart', {})


def save_cart(cart):
    session['cart'] = cart


def get_wishlist():
    return session.get('wishlist', [])


def cart_total(cart):
    total = 0
    for item in cart.values():
        product = Product.query.get(item['product_id'])
        if product:
            total += product.price * item['quantity']
    return total


@main_bp.route('/')
def home():
    featured = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    return render_template('home.html', products=featured, categories=categories)


@main_bp.route('/products')
def products():
    search = request.args.get('q', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    query = Product.query
    if search:
        query = query.filter(text(f"products.name LIKE '%{search}%'"))
    if category:
        query = query.join(Category).filter(Category.slug == category)
    products = query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('products.html', products=products, categories=categories, search=search, selected_category=category)


@main_bp.route('/products/search')
def product_search():
    search = request.args.get('q', '')
    return render_template('products.html', products=[], categories=Category.query.all(), search=search, selected_category='')


@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    related = Product.query.filter(Product.category_id == product.category_id, Product.id != product.id).limit(4).all()
    return render_template('product_detail.html', product=product, reviews=reviews, related=related)


@main_bp.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)


@main_bp.route('/search')
def search():
    return redirect(url_for('main.products', q=request.args.get('q', '')))


@main_bp.route('/wishlist')
def wishlist():
    items = []
    for product_id in get_wishlist():
        product = Product.query.get(product_id)
        if product:
            items.append(product)
    return render_template('wishlist.html', items=items)


@main_bp.route('/wishlist/toggle/<int:product_id>', methods=['POST'])
def toggle_wishlist(product_id):
    wishlist = get_wishlist()
    if product_id in wishlist:
        wishlist.remove(product_id)
    else:
        wishlist.append(product_id)
    session['wishlist'] = wishlist
    return redirect(request.referrer or url_for('main.home'))


@main_bp.route('/cart')
def cart():
    cart = get_cart()
    items = []
    for item in cart.values():
        product = Product.query.get(item['product_id'])
        if product:
            items.append({'product': product, 'quantity': item['quantity']})
    total = sum(item['product'].price * item['quantity'] for item in items)
    return render_template('cart.html', items=items, total=total)


@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = get_cart()
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {'product_id': product_id, 'quantity': 1}
    save_cart(cart)
    flash('Item added to cart successfully.', 'success')
    next_url = request.args.get('next') or request.form.get('next') or request.referrer or url_for('main.products')
    return redirect(next_url)


@main_bp.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = get_cart()
    quantity = int(request.form.get('quantity', 1))
    if quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = {'product_id': product_id, 'quantity': quantity}
    save_cart(cart)
    next_url = request.args.get('next') or request.form.get('next') or url_for('main.cart')
    return redirect(next_url)


@main_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    next_url = request.args.get('next') or request.form.get('next') or url_for('main.cart')
    return redirect(next_url)


@main_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Login required before checkout.', 'warning')
        return redirect(url_for('main.login'))
    if request.args.get('preview') == 'true':
        return render_template('checkout.html', items=[], total=0, coupon=None, discount_amount=0, grand_total=0)
    cart = get_cart()
    if not cart:
        return redirect(url_for('main.cart'))
    items = []
    total = 0
    for item in cart.values():
        product = Product.query.get(item['product_id'])
        if product:
            items.append({'product': product, 'quantity': item['quantity']})
            total += product.price * item['quantity']
    coupon_code = request.args.get('coupon_code', '')
    coupon = Coupon.query.filter_by(code=coupon_code, active=True).first() if coupon_code else None
    discount_amount = 0
    if coupon and total >= coupon.minimum_order:
        if coupon.type == 'percentage':
            discount_amount = round(total * (coupon.discount / 100), 2)
        else:
            discount_amount = coupon.discount
    grand_total = round(total - discount_amount, 2)
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'COD')
        coupon_code_form = request.form.get('coupon_code')
        coupon = Coupon.query.filter_by(code=coupon_code_form).first() if coupon_code_form else None
        discount_amount = 0
        if coupon:
            if coupon.type == 'percentage':
                discount_amount = round(total * (coupon.discount / 100), 2)
            else:
                discount_amount = coupon.discount
        grand_total = round(total - discount_amount, 2)
        user = User.query.get(session['user_id'])
        order = Order(user_id=user.id, total=grand_total, status='Pending', payment_method=payment_method, coupon_code=coupon_code_form)
        db.session.add(order)
        db.session.commit()
        for item in items:
            db.session.add(OrderItem(order_id=order.id, product_id=item['product'].id, quantity=item['quantity'], price=item['product'].price))
        db.session.commit()
        session['cart'] = {}
        flash('Order placed successfully.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('checkout.html', items=items, total=total, coupon=coupon, discount_amount=discount_amount, grand_total=grand_total)


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')

        if not name or not username or not email or not password:
            flash('Please fill in your name, username, email, and password.', 'danger')
            return redirect(url_for('main.register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('That username or email is already registered.', 'danger')
            return redirect(url_for('main.register'))

        user = User(name=name, username=username, email=email, phone=phone, address=address)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash('Registration successful.', 'success')
        return redirect(url_for('main.home'))
    return render_template('register.html')


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next', '')
    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        password = request.form.get('password', '')
        user = User.authenticate(identifier, password)
        if user:
            session['user_id'] = user.id
            flash('Login successful.', 'success')
            return redirect(next_url or url_for('main.home'))
        flash('Invalid username/email or password.', 'danger')
        return redirect(url_for('main.login', next=next_url))
    return render_template('login.html', next_url=next_url)


@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(request.args.get('next', url_for('main.home')))


@main_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account is registered with that email address.', 'danger')
            return render_template('forgot_password.html')
        token = secrets.token_hex(6)
        db.session.add(PasswordResetToken(email=email, token=token))
        db.session.commit()
        flash('A password reset link has been sent to your registered email address.', 'success')
        return render_template('forgot_password.html')
    return render_template('forgot_password.html')


@main_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    if not reset_token:
        flash('Invalid reset token.', 'danger')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        user = User.query.filter_by(email=reset_token.email).first()
        if user:
            user.set_password(request.form['password'])
            db.session.commit()
            flash('Password reset successful.', 'success')
            return redirect(url_for('main.login'))
    return render_template('reset_password.html', token=token)


@main_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    user = User.query.get(session['user_id'])
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', user=user, orders=orders)


@main_bp.route('/order/<int:order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    order = Order.query.get_or_404(order_id)
    return render_template('order_detail.html', order=order)


@main_bp.route('/product/<int:product_id>/review', methods=['POST'])
def submit_review(product_id):
    product = Product.query.get_or_404(product_id)
    comment = request.form.get('comment', '')
    rating = request.form.get('rating', 5, type=int)
    if 'user_id' not in session:
        flash('Login required to review.', 'warning')
        return redirect(url_for('main.login'))
    review = Review(user_id=session['user_id'], product_id=product.id, rating=rating, comment=comment)
    db.session.add(review)
    db.session.commit()
    flash('Review submitted.', 'success')
    return redirect(url_for('main.product_detail', product_id=product.id))


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for contacting GlowCart. Our team will reach out shortly.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')


@main_bp.route('/contact/import')
def contact_import():
    import pickle
    payload = request.args.get('payload', '')
    try:
        obj = pickle.loads(payload.encode('latin1'))
        deserialization_result = f'Deserialized object: {obj}'
    except Exception as exc:
        deserialization_result = f'Deserialization attempted: {type(exc).__name__}'
    return render_template('contact.html', deserialization_result=deserialization_result)


@main_bp.route('/contact/upload', methods=['POST'])
def contact_upload():
    file = request.files.get('attachment')
    if file and file.filename:
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        filename = file.filename
        path = os.path.join(UPLOADS_DIR, filename)
        file.save(path)
    return redirect(url_for('main.contact'))


@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    path = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=False)
    return 'File not found', 404


@main_bp.route('/download/<path:filename>')
def download_file(filename):
    path = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(path):
        with open(path, 'rb') as fh:
            return fh.read(), 200, {'Content-Type': 'application/octet-stream'}
    return 'File not found', 404


@main_bp.route('/about')
def about():
    return render_template('about.html')
