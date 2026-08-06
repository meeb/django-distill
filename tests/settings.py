from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True
SECRET_KEY = "test"
ROOT_URLCONF = "tests.urls"
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "distill.sqlite3",
        "TEST": {
            "NAME": BASE_DIR / "distill-tests.sqlite3",
        },
    }
}


INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "django.contrib.redirects",
    "django_distill",
    "tests",
]


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(name)s [%(levelname)s] %(message)s"},
    },
    "handlers": {
        "log_to_stdout": {
            "level": "ERROR",  # Switch to INFO to see test file rendering
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "main": {
            "handlers": ["log_to_stdout"],
            "level": "INFO",
            "propagate": True,
        }
    },
}


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "tests" / "templates"],
        "APP_DIRS": True,
    },
]


DISTILL_PUBLISH = {
    "test-s3-container": {
        "ENGINE": "django_distill.publishers.amazon_s3",
        "PUBLIC_URL": "https://test-public-url/",
        "ACCESS_KEY_ID": "test-access-key",
        "SECRET_ACCESS_KEY": "test-secret-key",
        "BUCKET": "test-bucket",
        "ENDPOINT_URL": "https://test-endpoint-url/",
        "DEFAULT_CONTENT_TYPE": "application/octet-stream",
    }
}


SITE_ID = 1


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "tests" / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "tests" / "media"


LANGUAGE_CODE = "en"
USE_I18N = True
