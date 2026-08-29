import os
import sys

os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
for module_name in ['config', 'models', 'app', 'routes.admin', 'routes.main']:
    sys.modules.pop(module_name, None)

import app as app_module

app = app_module.app


def test_contact_import_renders_deserialization_result_on_page():
    client = app.test_client()
    response = client.get('/contact/import?payload=')
    assert response.status_code == 200
    assert b'Deserialization attempted' in response.data

    response = client.get('/contact/import?payload=%28i%20x%20x%20x%29')
    assert response.status_code == 200
    assert b'Order / Request Reference' in response.data
    assert b'payload' in response.data
