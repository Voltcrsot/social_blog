# users/apps.py

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = "Пользователи и Профили" # Название в админке

    def ready(self):
        """Импортируем сигналы при готовности приложения."""
        try:
            # Если бы сигналы были в отдельном файле signals.py
            import users.signals # noqa: F401
        except ImportError:
            # Так как сигналы у нас в models.py, импортируем его
            import users.models # noqa: F401