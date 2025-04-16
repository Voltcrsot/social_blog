# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# --- ДОБАВЛЕН ИМПОРТ ---
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
# ----------------------

urlpatterns = [
    path('admin/', admin.site.urls),

    # Подключаем URL нашего приложения users
    path('users/', include('users.urls', namespace='users')),

    # Приложение posts в корне
    path('', include('posts.urls', namespace='posts')),

    # --- ДОБАВЛЕНО: URL для django-components (если используется) ---
    path('components/', include('django_components.urls')),
    # --------------------------------------------------------------
]

# --- ИЗМЕНЕНО: Обработка статики и медиа ---
if settings.DEBUG:
    # Сначала добавляем обработчики статики и медиа
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Используем staticfiles_urlpatterns для статики приложений
    urlpatterns += staticfiles_urlpatterns()
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

# --- ИЗМЕНЕНО: Подключение Debug Toolbar ПОСЛЕ всех остальных URL ---
if settings.DEBUG:
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        # Добавляем URL debug_toolbar в КОНЕЦ списка urlpatterns
        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
# --- КОНЕЦ ИЗМЕНЕНИЯ ---