import os
os.chdir(r'c:\Glow Cart')
from app import app

client = app.test_client()
response = client.get('/categories')
print(response.status_code)
print('Browse by category' in response.get_data(as_text=True))
