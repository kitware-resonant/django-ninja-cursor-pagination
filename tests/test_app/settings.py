ROOT_URLCONF = "test_app.urls"
SECRET_KEY = "insecure-secret"

INSTALLED_APPS = [
    "test_app",
    "ninja",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
