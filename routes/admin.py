import os
import re
import secrets
from urllib.parse import urlparse

import requests
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from models import Category, Coupon, Order, OrderItem, Product, Review, Upload, User, db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_logged_in():
    return session.get('admin_logged_in')


def _build_slug(value):
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'product'


def _save_uploaded_image(file):
    if not file or not getattr(file, 'filename', ''):
        return None

    filename = os.path.basename(file.filename)
    os.makedirs('uploads', exist_ok=True)
    destination = os.path.join('uploads', filename)
    if os.path.exists(destination):
        base_name, file_ext = os.path.splitext(filename)
        filename = f"{base_name}-{secrets.token_hex(4)}{file_ext}"
        destination = os.path.join('uploads', filename)

    file.save(destination)
    db.session.add(Upload(filename=filename, original_name=file.filename, uploaded_by='admin'))
    return '/uploads/' + filename


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        next_url = request.args.get('next', '')
        from models import Admin

        admin = Admin.authenticate(identifier, password)
        if admin:
            session['admin_logged_in'] = True
            flash('Admin login successful.', 'success')
            return redirect(next_url or url_for('admin.dashboard'))
        flash('Invalid admin credentials.', 'danger')
        return redirect(url_for('admin.login', next=next_url))
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
def dashboard():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    product_count = Product.query.count()
    order_count = Order.query.count()
    customer_count = User.query.count()
    revenue = sum(order.total for order in Order.query.all())
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', product_count=product_count, order_count=order_count,
                           customer_count=customer_count, revenue=revenue, recent_orders=recent_orders)


@admin_bp.route('/products')
def products():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))

    categories = Category.query.all()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        slug = (request.form.get('slug') or '').strip()
        description = (request.form.get('description') or '').strip()
        short_description = (request.form.get('short_description') or '').strip()
        price = request.form.get('price', '0')
        compare_price = request.form.get('compare_price', '0')
        stock = request.form.get('stock', '10')
        category_id = request.form.get('category_id', '0')
        image = (request.form.get('image') or '').strip()

        if not name or not description:
            flash('Please provide a product name and description.', 'danger')
            return render_template('admin/products_form.html', categories=categories, product=None, is_edit=False)

        try:
            price = float(price)
            compare_price = float(compare_price or 0)
            stock = int(stock or 10)
            category_id = int(category_id)
        except (TypeError, ValueError):
            flash('Please enter valid numeric values for price, compare price, and stock.', 'danger')
            return render_template('admin/products_form.html', categories=categories, product=None, is_edit=False)

        if not slug:
            slug = _build_slug(name)

        try:
            uploaded_image = _save_uploaded_image(request.files.get('image_file'))
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('admin/products_form.html', categories=categories, product=None, is_edit=False)

        if uploaded_image:
            image = uploaded_image
        elif not image:
            image = 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'

        product = Product(name=name, slug=slug, description=description, short_description=short_description,
                          price=price, compare_price=compare_price, stock=stock, category_id=category_id, image=image)
        db.session.add(product)
        db.session.commit()
        flash('Product added.', 'success')
        return redirect(url_for('admin.products'))

    return render_template('admin/products_form.html', categories=categories, product=None, is_edit=False)


@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    if not admin_logged_in():
        return redirect(url_for('admin.login'))

    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        slug = (request.form.get('slug') or '').strip()
        description = (request.form.get('description') or '').strip()
        short_description = (request.form.get('short_description') or '').strip()
        price = request.form.get('price', '0')
        compare_price = request.form.get('compare_price', '0')
        stock = request.form.get('stock', '10')
        category_id = request.form.get('category_id', '0')
        image = (request.form.get('image') or '').strip()

        if not name or not description:
            flash('Please provide a product name and description.', 'danger')
            return render_template('admin/products_form.html', categories=categories, product=product, is_edit=True)

        try:
            price = float(price)
            compare_price = float(compare_price or 0)
            stock = int(stock or 10)
            category_id = int(category_id)
        except (TypeError, ValueError):
            flash('Please enter valid numeric values for price, compare price, and stock.', 'danger')
            return render_template('admin/products_form.html', categories=categories, product=product, is_edit=True)

        if not slug:
            slug = _build_slug(name)

        try:
            uploaded_image = _save_uploaded_image(request.files.get('image_file'))
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('admin/products_form.html', categories=categories, product=product, is_edit=True)

        product.name = name
        product.slug = slug
        product.description = description
        product.short_description = short_description
        product.price = price
        product.compare_price = compare_price
        product.stock = stock
        product.category_id = category_id
        if uploaded_image:
            product.image = uploaded_image
        elif image:
            product.image = image

        db.session.commit()
        flash('Product updated.', 'success')
        return redirect(url_for('admin.products'))

    return render_template('admin/products_form.html', categories=categories, product=product, is_edit=True)


@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    if not admin_logged_in():
        return redirect(url_for('admin.login'))

    product = Product.query.get_or_404(product_id)
    Review.query.filter_by(product_id=product.id).delete(synchronize_session=False)
    OrderItem.query.filter_by(product_id=product.id).delete(synchronize_session=False)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/import-url', methods=['POST'])
def import_product_url():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    url = request.form.get('image_url', '')
    if url:
        try:
            response = requests.get(url, timeout=5)
            if response.ok:
                filename = os.path.basename(url.split('/')[-1]) or 'image.jpg'
                path = os.path.join('uploads', filename)
                with open(path, 'wb') as fh:
                    fh.write(response.content)
                return redirect(url_for('admin.products'))
        except Exception:
            pass
    flash('Could not import image.', 'danger')
    return redirect(url_for('admin.products'))


@admin_bp.route('/categories')
def categories():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    if request.method == 'POST':
        name = request.form['name']
        slug = request.form['slug']
        description = request.form['description']
        category = Category(name=name, slug=slug, description=description)
        db.session.add(category)
        db.session.commit()
        flash('Category added.', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/categories_form.html')


@admin_bp.route('/orders')
def orders():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@admin_bp.route('/users')
def users():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/customers')
def customers():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    return redirect(url_for('admin.users'))


@admin_bp.route('/uploads')
def uploads():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    uploads = Upload.query.order_by(Upload.created_at.desc()).all()
    return render_template('admin/uploads.html', uploads=uploads)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not admin_logged_in():
        return redirect(url_for('admin.login'))

    user = User.query.get_or_404(user_id)
    order_ids = [order.id for order in Order.query.filter_by(user_id=user.id).all()]
    if order_ids:
        OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
    Review.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    Order.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    flash('User account deleted successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/coupons')
def coupons():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    coupons = Coupon.query.all()
    return render_template('admin/coupons.html', coupons=coupons)


@admin_bp.route('/coupons/add', methods=['GET', 'POST'])
def add_coupon():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    if request.method == 'POST':
        code = request.form['code']
        discount = float(request.form['discount'])
        type_ = request.form['type']
        minimum_order = float(request.form.get('minimum_order', 0))
        coupon = Coupon(code=code, discount=discount, type=type_, minimum_order=minimum_order)
        db.session.add(coupon)
        db.session.commit()
        flash('Coupon added.', 'success')
        return redirect(url_for('admin.coupons'))
    return render_template('admin/coupons_form.html')


@admin_bp.route('/uploads')
def uploads():
    if not admin_logged_in():
        return redirect(url_for('admin.login'))
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/')
def admin_home():
    return redirect(url_for('admin.login'))
