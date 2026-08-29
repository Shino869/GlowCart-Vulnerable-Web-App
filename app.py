from flask import Flask, render_template, request, session, redirect, url_for, flash, g
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from sqlalchemy import inspect, text
from config import SQLALCHEMY_DATABASE_URI, DEBUG, SECRET_KEY, UPLOADS_DIR, ALLOWED_EXTENSIONS
from models import db, User, Admin, Category, Product, Review, Coupon, Order, OrderItem, Upload, PasswordResetToken
from routes.main import main_bp
from routes.admin import admin_bp
import os
import secrets
import traceback
import requests
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOADS_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['DEBUG'] = DEBUG
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = None

if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
    os.makedirs('instance', exist_ok=True)


db.init_app(app)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)


CATEGORY_DEFINITIONS = [
    ('Skincare', 'skincare', 'Radiant daily essentials'),
    ('Makeup', 'makeup', 'Color-forward and buildable formulas'),
    ('Haircare', 'haircare', 'Shine, softness, and smooth styling'),
    ('Fragrance', 'fragrance', 'Warm floral and signature scents'),
    ('Tools', 'tools', 'Beauty applicators and finishing tools'),
]

PRODUCT_DEFINITIONS = [
    {'name': 'Face Moisturizer', 'slug': 'face-moisturizer', 'description': 'A velvety daily moisturizer that hydrates, softens, and leaves skin looking radiant and balanced.', 'price': 54, 'compare_price': 72, 'image': 'https://www.verywellhealth.com/thmb/Z8xM8ZtPiZKwAIHobCTGe9az_2A=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/75167041-56a245445f9b58b7d0c8791e.jpg', 'category_slug': 'skincare', 'stock': 15, 'rating': 4.5},
    {'name': 'Facewash', 'slug': 'facewash', 'description': 'A gentle foaming cleanser designed to refresh the skin while removing impurities without over-drying.', 'price': 38, 'compare_price': 50, 'image': 'https://smytten.com/blogs/_next/image?url=https%3A%2F%2Fd1msew97rp2nin.cloudfront.net%2Fprodin%2Fsmyttenshop%2Fblogimages%2Fhow-to-use-salicylic-acid-face-wash-for-clearer-skin-in-india-9d46cd9c-aacb-4079-8c1c-6513e91bf2d8.webp&w=3840&q=75', 'category_slug': 'skincare', 'stock': 15, 'rating': 4.5},
    {'name': 'Serum', 'slug': 'serum', 'description': 'A lightweight serum infused with potent actives to boost glow, smooth texture, and support a healthy-looking complexion.', 'price': 68, 'compare_price': 89, 'image': 'https://images.squarespace-cdn.com/content/v1/5c4f6ba1e2ccd1ee6075495d/232540bb-2961-4299-8dc3-169fd7f110ab/face-serums.jpg', 'category_slug': 'skincare', 'stock': 15, 'rating': 4.5},
    {'name': 'Sunscreen SPF 50', 'slug': 'sunscreen-spf-50', 'description': 'Broad-spectrum SPF 50 protection in a light, comfortable formula that layers beautifully under makeup.', 'price': 42, 'compare_price': 55, 'image': 'https://smytten.com/blogs/_next/image?url=https%3A%2F%2Fd1msew97rp2nin.cloudfront.net%2Fprodin%2Fsmyttenshop%2Fblogimages%2F7-top-sunscreens-perfect-for-indian-skin-types-3c5c7998-75f4-4578-9d51-82beaf302f3f.webp&w=3840&q=75', 'category_slug': 'skincare', 'stock': 15, 'rating': 4.5},
    {'name': 'Toner', 'slug': 'toner', 'description': 'A refreshing toner that balances, tones, and preps the skin for the rest of your routine.', 'price': 35, 'compare_price': 46, 'image': 'https://www.bodycraft.co.in/hubfs/Imported_Blog_Media/facial-toner-1.png', 'category_slug': 'skincare', 'stock': 15, 'rating': 4.5},
    {'name': 'Lipstick', 'slug': 'lipstick', 'description': 'A rich, long-wearing lipstick with a satin finish that delivers bold color and everyday elegance.', 'price': 29, 'compare_price': 40, 'image': 'https://ibacosmetics.com/cdn/shop/products/IbaPureLipsMoistureRichLipstick-A35DarkChocolate.jpg?v=1658229312&width=800', 'category_slug': 'makeup', 'stock': 15, 'rating': 4.5},
    {'name': 'Lip Balm', 'slug': 'lip-balm', 'description': 'A nourishing lip balm that hydrates and smooths lips with a soft, glossy finish.', 'price': 18, 'compare_price': 25, 'image': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSqKr-1h2lGrLh5SRqm5WOK35OnTghIMsygBoyiduCEFjvVqTGvwgSvetZA&s=10', 'category_slug': 'makeup', 'stock': 15, 'rating': 4.5},
    {'name': 'Eye Palette', 'slug': 'eye-palette', 'description': 'A premium eye palette with versatile shades designed for effortless blending and striking definition.', 'price': 57, 'compare_price': 70, 'image': 'https://hilaryrhoda.in/cdn/shop/files/2_0d9bfa57-b792-4ff4-ac2a-b5e00f6d8dee.jpg?v=1755456520', 'category_slug': 'makeup', 'stock': 15, 'rating': 4.5},
    {'name': 'Foundation', 'slug': 'foundation', 'description': 'A flawless, buildable foundation that gives skin a natural, polished finish with lasting comfort.', 'price': 74, 'compare_price': 95, 'image': 'https://lustminerals.com.au/cdn/shop/files/Matte_Finish_Liquid_Foundation.png?v=1731048361', 'category_slug': 'makeup', 'stock': 15, 'rating': 4.5},
    {'name': 'Shampoo', 'slug': 'shampoo', 'description': 'A luxurious shampoo that cleanses gently while leaving hair soft, shiny, and full of body.', 'price': 44, 'compare_price': 58, 'image': 'https://lovebeautyandplanet.in/cdn/shop/articles/washing-hair-featured-image--1.jpg?v=1701447548', 'category_slug': 'haircare', 'stock': 15, 'rating': 4.5},
    {'name': 'Hair Serum', 'slug': 'hair-serum', 'description': 'A smoothing hair serum that tames frizz, adds shine, and helps hair look effortlessly polished.', 'price': 52, 'compare_price': 66, 'image': 'https://m.media-amazon.com/images/I/71gHHpChFCL.jpg', 'category_slug': 'haircare', 'stock': 15, 'rating': 4.5},
    {'name': 'Conditioner', 'slug': 'conditioner', 'description': 'A rich conditioner that delivers deep hydration and silky softness with every use.', 'price': 46, 'compare_price': 60, 'image': 'https://www.tresemme.in/cdn/shop/articles/Conditioning_for_Success.jpg?v=1727246563&width=1100', 'category_slug': 'haircare', 'stock': 15, 'rating': 4.5},
    {'name': 'Velvet Bloom Perfume', 'slug': 'velvet-bloom-perfume', 'description': 'An elegant floral fragrance with a soft, luxurious trail that feels timeless and refined.', 'price': 92, 'compare_price': 116, 'image': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTfEVSCJpGgr2bd46GKbwAc5wXf0zTitvrolsIn0jqaAmICfJqZugwqRWE&s=10', 'category_slug': 'fragrance', 'stock': 15, 'rating': 4.5},
    {'name': 'Rose Gold Brush Kit', 'slug': 'rose-gold-brush-kit', 'description': 'A beautifully crafted brush kit designed for smooth application and professional-looking results.', 'price': 82, 'compare_price': 100, 'image': 'https://m.media-amazon.com/images/I/71O-x2ohIZL._AC_UF1000,1000_QL80_.jpg', 'category_slug': 'tools', 'stock': 15, 'rating': 4.5},
]


def sync_catalog_data():
    for name, slug, desc in CATEGORY_DEFINITIONS:
        category = Category.query.filter_by(slug=slug).first()
        if category:
            category.name = name
            category.description = desc
        else:
            category = Category(name=name, slug=slug, description=desc)
            db.session.add(category)
    db.session.commit()

    category_map = {cat.slug: cat for cat in Category.query.all()}
    active_slugs = {product_data['slug'] for product_data in PRODUCT_DEFINITIONS}

    for product in Product.query.all():
        if product.slug in active_slugs:
            continue
        Review.query.filter_by(product_id=product.id).delete(synchronize_session=False)
        OrderItem.query.filter_by(product_id=product.id).delete(synchronize_session=False)
        db.session.delete(product)
    db.session.commit()

    for product_data in PRODUCT_DEFINITIONS:
        category = category_map.get(product_data['category_slug'])
        if not category:
            continue

        product = Product.query.filter_by(slug=product_data['slug']).first()
        if product:
            product.name = product_data['name']
            product.description = product_data['description']
            product.short_description = product_data.get('short_description', product_data['description'])
            product.price = product_data['price']
            product.compare_price = product_data['compare_price']
            product.image = product_data['image']
            product.category_id = category.id
            product.stock = product_data.get('stock', product.stock)
            product.rating = product_data.get('rating', product.rating)
        else:
            product = Product(
                name=product_data['name'],
                slug=product_data['slug'],
                description=product_data['description'],
                short_description=product_data.get('short_description', product_data['description']),
                price=product_data['price'],
                compare_price=product_data['compare_price'],
                image=product_data['image'],
                category=category,
                stock=product_data.get('stock', 15),
                rating=product_data.get('rating', 4.5),
            )
            db.session.add(product)
    db.session.commit()


def ensure_database_schema():
    inspector = inspect(db.engine)
    if 'users' in inspector.get_table_names():
        user_columns = {column['name'] for column in inspector.get_columns('users')}
        if 'username' not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE users ADD COLUMN username VARCHAR(80) NULL'))
        if 'password_plaintext' not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE users ADD COLUMN password_plaintext VARCHAR(255) NULL'))
    if 'admins' in inspector.get_table_names():
        admin_columns = {column['name'] for column in inspector.get_columns('admins')}
        if 'email' not in admin_columns:
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE admins ADD COLUMN email VARCHAR(120) NULL'))


def seed_data():
    sync_catalog_data()

    if User.query.count() == 0:
        users = [
            ('Ava Carter', 'ava', 'ava@example.com', 'password123', '555-1010', '12 Rose Avenue'),
            ('Liam Brooks', 'liam', 'liam@example.com', 'password123', '555-1020', '9 Lavender Lane'),
            ('Mia Fernandez', 'mia', 'mia@example.com', 'password123', '555-1030', '18 Pearl Drive'),
            ('Noah Patel', 'noah', 'noah@example.com', 'password123', '555-1040', '24 Orchid Road'),
            ('Sophia Reed', 'sophia', 'sophia@example.com', 'password123', '555-1050', '30 Petal Court'),
            ('Ethan Young', 'ethan', 'ethan@example.com', 'password123', '555-1060', '6 Velvet Way'),
            ('Isabella Gray', 'isabella', 'isabella@example.com', 'password123', '555-1070', '14 Bloom Street'),
            ('Mason Walker', 'mason', 'mason@example.com', 'password123', '555-1080', '50 Coral Plaza'),
            ('Charlotte Turner', 'charlotte', 'charlotte@example.com', 'password123', '555-1090', '76 Aura Avenue'),
            ('James Hughes', 'james', 'james@example.com', 'password123', '555-1100', '91 Serenity Lane'),
        ]
        for name, username, email, pwd, phone, address in users:
            user = User(name=name, username=username, email=email, phone=phone, address=address)
            user.set_password(pwd)
            user.password_plaintext = pwd
            db.session.add(user)
        db.session.commit()
    else:
        password_map = {
            'ava@example.com': 'ava123',
            'liam@example.com': 'liam123',
            'mia@example.com': 'mia123',
            'noah@example.com': 'noah123',
            'sophia@example.com': 'sophia123',
            'ethan@example.com': 'ethan123',
            'isabella@example.com': 'isabella123',
            'mason@example.com': 'mason123',
            'charlotte@example.com': 'charlotte123',
            'james@example.com': 'james123',
        }
        for user in User.query.all():
            if user.email in password_map:
                password = password_map[user.email]
                user.set_password(password)
                user.password_plaintext = password
        db.session.commit()

    if Admin.query.count() == 0:
        admin = Admin(username='admin', email='admin@example.com', password_hash='')
        admin.set_password('admin123')
        db.session.add(admin)
    else:
        admin = Admin.query.filter_by(username='admin').first()
        if admin:
            admin.set_password('admin123')
    db.session.commit()

    if Coupon.query.count() == 0:
        coupons = [
            ('GLOW10', 10, 'percentage', 40, True),
            ('GLOW20', 20, 'percentage', 80, True),
            ('ROSE25', 25, 'percentage', 100, True),
            ('SAVE50', 50, 'fixed', 120, True),
            ('VIP15', 15, 'percentage', 60, True),
        ]
        for code, discount, typ, minimum_order, active in coupons:
            db.session.add(Coupon(code=code, discount=discount, type=typ, minimum_order=minimum_order, active=active))
    db.session.commit()

    if Review.query.count() == 0:
        products = Product.query.all()
        users = User.query.all()
        comments = [
            'Smooth and expensive-feeling finish.', 'My skin feels hydrated all day.', 'A lovely, wearable shade that looks polished.',
            'Beautiful packaging and a rich texture.', 'Worth the premium price for the glow it gives.', 'I have repurchased this twice.',
            'The fragrance is soft and elegant.', 'Perfect for gifting and everyday use.', 'Super easy to apply and blends well.',
            'Love how long it stays on my skin.', 'A gorgeous favorite for my routine.', 'This feels luxurious and clean.',
            'The formula is so smooth and silky.', 'The scent is delicate without overpowering.', 'Great for minimal makeup days.',
            'The finish is radiant yet natural.', 'This is one of my top picks this season.', 'Very reliable quality.',
        ]
        for i in range(25):
            product = products[i % len(products)]
            user = users[i % len(users)]
            db.session.add(Review(user_id=user.id, product_id=product.id, rating=4 + (i % 2), comment=comments[i % len(comments)]))
    db.session.commit()

    if Order.query.count() == 0:
        for i in range(12):
            user = User.query.order_by(User.id).offset(i % 10).first()
            order = Order(user_id=user.id, total=120 + i * 12, status=['Pending', 'Processing', 'Shipped', 'Delivered'][i % 4], payment_method=['COD', 'Online'][i % 2], coupon_code='GLOW10' if i % 2 == 0 else None)
            db.session.add(order)
        db.session.commit()
        orders = Order.query.all()
        products = Product.query.all()
        for idx, order in enumerate(orders):
            product = products[idx % len(products)]
            db.session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1 + (idx % 2), price=product.price))
    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_database_schema()
    seed_data()


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    if isinstance(e, HTTPException):
        return e
    return render_template('500.html', stack_trace=traceback.format_exc()), 500


@app.before_request
def load_session_user():
    g.user = None
    if session.get('user_id'):
        g.user = User.query.get(session['user_id'])


@app.after_request
def no_cache_response(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response



if __name__ == '__main__':
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    app.run(host='127.0.0.1', port=5000, debug=DEBUG, use_reloader=False)
