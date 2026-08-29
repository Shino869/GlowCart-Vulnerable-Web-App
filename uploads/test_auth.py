import unittest

from flask import Flask

from models import User, db


class UserAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()
            user = User(name='Test User', email='tester@example.com', username='tester')
            user.set_password('secret123')
            db.session.add(user)
            db.session.commit()

    def test_auth_accepts_username_or_email(self):
        with self.app.app_context():
            self.assertIsNotNone(User.authenticate('tester', 'secret123'))
            self.assertIsNotNone(User.authenticate('tester@example.com', 'secret123'))
            self.assertIsNone(User.authenticate('tester', 'wrong-password'))


if __name__ == '__main__':
    unittest.main()
