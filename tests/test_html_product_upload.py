import importlib
import io
import os
import sys

os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
for module_name in ['config', 'models', 'app', 'routes.admin', 'routes.main']:
    sys.modules.pop(module_name, None)

import config
import models
import app as app_module

app = app_module.app
UPLOADS_DIR = config.UPLOADS_DIR
Category = models.Category
Product = models.Product
db = models.db


def test_admin_can_upload_html_product_image_and_render_it_as_link():
    with app.app_context():
        db.drop_all()
        db.create_all()

        category = Category(name='Test Category', slug='test-category', description='Test')
        db.session.add(category)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session['admin_logged_in'] = True

        response = client.post(
            '/admin/products/add',
            data={
                'name': 'HTML Demo Product',
                'slug': 'html-demo-product',
                'description': 'Product description',
                'short_description': 'Short description',
                'price': '19.99',
                'compare_price': '29.99',
                'stock': '10',
                'category_id': str(category.id),
                'image': '',
                'image_file': (io.BytesIO(b'<html><body>hello</body></html>'), 'demo.html'),
            },
            content_type='multipart/form-data',
        )

        assert response.status_code == 302

        product = Product.query.filter_by(slug='html-demo-product').first()
        assert product is not None
        assert product.image.endswith('/demo.html')
        assert os.path.exists(os.path.join(UPLOADS_DIR, 'demo.html'))

        detail_response = client.get(f'/product/{product.id}')
        assert detail_response.status_code == 200
        assert b'target="_blank"' in detail_response.data
        assert b'/uploads/demo.html' in detail_response.data
