# config/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-fallback-key-needs-to-be-changed!")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1 localhost").split(" ")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', # Стандартная аутентификация Django
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party Apps
    'tailwind',
    'django_components',
    'debug_toolbar',
    'widget_tweaks',

    # Local Apps
    'theme.apps.ThemeConfig',
    'users.apps.UsersConfig',
    'posts.apps.PostsConfig',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", # Важно для сессий
    # --- ДОБАВЛЕНО (Опционально): Кеширование всей страницы ---
    # Если хочешь кешировать страницы целиком (требует осторожности с динамическим контентом)
    # 'django.middleware.cache.UpdateCacheMiddleware',
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.cache.FetchFromCacheMiddleware', # Должен быть после UpdateCacheMiddleware
    # --- КОНЕЦ ДОБАВЛЕННОГО ---
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", # Стандартный middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth", # Для user в шаблонах
                "django.contrib.messages.context_processors.messages",
                "posts.context_processors.categories_processor", # Наш контекст-процессор
            ],
            "builtins": [
                 "django.templatetags.cache", # <-- ДОБАВЛЕНО: для тега {% cache %}
                 "django_components.templatetags.component_tags",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                 "django_components.template_loader.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- ДОБАВЛЕНО: Настройки кеширования ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Убедись, что этот путь соответствует твоему запущенному Redis серверу
        "LOCATION": "redis://127.0.0.1:6379/0", # База данных 0
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # "CONNECTION_POOL_KWARGS": {"max_connections": 100}, # Опционально
            # "PASSWORD": "your_redis_password", # Раскомментируй и вставь пароль, если он есть
        }
        # "TIMEOUT": 300, # Опционально: Таймаут по умолчанию (5 минут)
    }
    # Можно добавить другие кеши, например, для сессий:
    # "sessions": { ... }
}
# --- КОНЕЦ ДОБАВЛЕННОГО БЛОКА ---

# --- Опционально: Хранение сессий в Redis ---
# Раскомментируй, если хочешь хранить сессии в Redis (используя кеш 'default')
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"
# ------------------------------------------------

# Валидаторы паролей Django
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", },
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", },
]

# --- Настройки для стандартной аутентификации Django ---
LOGIN_URL = 'users:login'       # Имя URL-шаблона для страницы входа
LOGIN_REDIRECT_URL = '/'      # Куда перенаправлять после успешного входа
LOGOUT_REDIRECT_URL = '/'     # Куда перенаправлять после выхода
# ----------------------------------------------------

# --- Настройки интернационализации ---
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# --- Настройки статики и медиа ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",  # Для общих статических файлов проекта (если есть)
    BASE_DIR / "theme" / "static", # Явно указываем, где искать статику темы (включая сборку)
]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- Прочее ---
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Настройки Email ---
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend" # Вывод в консоль для разработки
    DEFAULT_FROM_EMAIL = 'webmaster@localhost'
else:
    # Настройте реальный SMTP сервер для продакшена
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.example.com")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or 'noreply@yourdomain.com')

# --- Настройки сторонних приложений ---
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1", ] # Для debug_toolbar
NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd" # Если нужно
DEBUG_TOOLBAR_CONFIG = { # Для debug_toolbar
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}