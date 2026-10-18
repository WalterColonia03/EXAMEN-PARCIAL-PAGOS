from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_env_path = BASE_DIR / ".env"
if _env_path.is_file():
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _val = _line.split("=", 1)
            _key = _key.strip()
            _val = _val.strip().strip("'\"")
            os.environ.setdefault(_key, _val)

DEBUG = os.environ.get("DJANGO_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Clave exclusiva para desarrollo local. Producción debe definir
        # DJANGO_SECRET_KEY de forma explícita.
        SECRET_KEY = "django-insecure-pagocontrol-local-development-only"
    else:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY cuando DJANGO_DEBUG=0.")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

# Aíslan este proyecto de otros servidores Django que el navegador pueda abrir
# en localhost, incluso si usan otro puerto.
SESSION_COOKIE_NAME = "pagocontrol_session"
CSRF_COOKIE_NAME = "pagocontrol_csrf"
CSRF_FAILURE_VIEW = "identity.views.csrf_failure"


def _environment_flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


# The demo shortcuts deliberately remain opt-in. They can only be enabled on a
# local development server, never in a production deployment. Normal access
# always requires the account password.
DEMO_ACCESS_ENABLED = DEBUG and _environment_flag("PAGOCONTROL_ENABLE_DEMO_ACCESS")
DEMO_ACCESS_ALLOWED_HOSTS = {
    host.strip().lower()
    for host in os.environ.get("PAGOCONTROL_DEMO_ACCESS_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
}
DEMO_MANAGER_EMAIL = os.environ.get("PAGOCONTROL_DEMO_MANAGER_EMAIL", "gerente.demo@pagos.invalid")
DEMO_ASSISTANT_EMAIL = os.environ.get("PAGOCONTROL_DEMO_ASSISTANT_EMAIL", "asistente.demo@pagos.invalid")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "identity.apps.IdentityConfig",
    "payments.apps.PaymentsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL:
    # Vercel abre conexiones efímeras. Supabase recomienda su pooler de
    # transacciones para este tipo de runtime, por lo que Django no conserva
    # conexiones entre invocaciones.
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("prepare_threshold", None)
    DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 10)
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "identity.Account"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "private_uploads"
MEDIA_URL = "/media/"

_SUPABASE_STORAGE_ENV = {
    "bucket_name": os.environ.get("SUPABASE_STORAGE_BUCKET", "").strip(),
    "endpoint_url": os.environ.get("SUPABASE_S3_ENDPOINT_URL", "").strip(),
    "region_name": os.environ.get("SUPABASE_S3_REGION", "").strip(),
    "access_key": os.environ.get("SUPABASE_S3_ACCESS_KEY_ID", "").strip(),
    "secret_key": os.environ.get("SUPABASE_S3_SECRET_ACCESS_KEY", "").strip(),
}

USE_SUPABASE_STORAGE = any(_SUPABASE_STORAGE_ENV.values())

if USE_SUPABASE_STORAGE:
    missing_storage_values = [
        name for name, value in _SUPABASE_STORAGE_ENV.items() if not value
    ]
    if missing_storage_values:
        raise ImproperlyConfigured(
            "La configuración de Supabase Storage está incompleta: "
            + ", ".join(missing_storage_values)
            + "."
        )
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                **_SUPABASE_STORAGE_ENV,
                "addressing_style": "path",
                "default_acl": None,
                "file_overwrite": False,
                "querystring_auth": True,
                "querystring_expire": int(os.environ.get("SUPABASE_SIGNED_URL_TTL", "60")),
                "signature_version": "s3v4",
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
elif not DEBUG:
    raise ImproperlyConfigured(
        "Producción requiere Supabase Storage privado para conservar los documentos adjuntos."
    )

# Vercel Functions limita solicitudes y respuestas a 4.5 MB. Dejamos margen
# para el contenedor multipart y mantenemos la validación funcional en 4 MB.
FILE_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4_400_000

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = os.environ.get("DJANGO_HSTS_PRELOAD", "0").strip() in {"1", "true", "yes", "on"}

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
