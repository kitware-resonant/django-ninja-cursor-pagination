INSTALLED_APPS = [
    "ninja",
    "someapp",
]

ROOT_URLCONF = "demo.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    },
}

USE_I18N = True
