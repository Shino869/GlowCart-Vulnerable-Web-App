
# GlowCart

GlowCart is a premium cosmetic shopping website built with Python Flask, SQLAlchemy, Bootstrap 5, and MySQL.

## Features

- Customer storefront: home, products, product details, categories, search, wishlist, cart, checkout, coupons, payment options, reviews, profile, order history, contact, about
- Admin panel: login, dashboard, products, categories, orders, customers, coupons, uploads
- MySQL-backed data model using SQLAlchemy
- Product image upload and URL import support

## Requirements

- Python 3.10+
- MySQL Server
- Flask dependencies listed in requirements.txt

## Installation

1. Clone or extract this project.
2. Create a virtual environment:
   python -m venv .venv
3. Activate the virtual environment:
   - Windows PowerShell: .\.venv\Scripts\Activate.ps1
4. Install dependencies:
   pip install -r requirements.txt
5. Create the MySQL database:
   mysql -u root -p < database.sql
6. Configure local environment variables (do not commit `.env`):
   - Copy `.env.example` to `.env` and set your local MySQL credentials.
   - On Windows PowerShell, you can also set `DATABASE_URL` directly:
     `$env:DATABASE_URL="mysql+pymysql://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:3306/glowcart?charset=utf8mb4"`
7. Start the app:
   python app.py

## Demo Admin Credentials

- Username: `admin`
- Password: `admin123`

These are intentionally hard-coded demo credentials for the local cybersecurity lab. 

## Notes

- The app uses Flask's built-in development server.
- Uploaded files are stored in the uploads folder.
- The app is intentionally built to match the requested project structure and feature set.


## Security Lab Notice

GlowCart is intentionally vulnerable and is provided for cybersecurity education,
Burp Suite testing, and authorized local security testing. Do not deploy this
application to the public internet in its intentionally vulnerable state.

The project includes intentionally insecure behavior such as file upload,
open redirect, account enumeration, information disclosure, business-logic
issues, directory listing, missing rate limiting, weak password reset,
HTML injection, and SSRF for controlled testing.

