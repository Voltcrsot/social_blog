# users/urls.py
from django.urls import path, reverse_lazy
# Импортируем ТОЛЬКО наши представления
from . import views
# Стандартные auth_views больше импортировать не нужно, т.к. мы используем свои классы-наследники

app_name = 'users'

urlpatterns = [
    # --- Аутентификация ---
    path('register/', views.user_register_view, name='register'), # Используем нашу view-функцию
    path('login/', views.user_login_view, name='login'),       # Используем нашу view-функцию
    path('logout/', views.user_logout_view, name='logout'),     # Используем нашу view-функцию

    # --- Профиль ---
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'), # Редактирование своего профиля

    # --- Подписки ---
    # URL для HTMX кнопки подписки/отписки
    path('<str:username>/toggle_follow/', views.toggle_follow_view, name='toggle_follow'),
    # URL для страницы со списком подписок пользователя
    path('<str:username>/following/', views.FollowingListView.as_view(), name='following_list'),
    # URL для страницы со списком подписчиков пользователя
    path('<str:username>/followers/', views.FollowersListView.as_view(), name='followers_list'),

    # --- Просмотр профиля (обычно идет последним как "catch-all" для username) ---
    path('<str:username>/', views.ProfileDetailView.as_view(), name='profile_detail'),

    # --- Сброс пароля (используем наши классы-наследники стандартных view) ---
    path('password_reset/', views.UserPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.UserPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.UserPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # --- Изменение пароля (для залогиненного пользователя) ---
    path('password_change/', views.UserPasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', views.UserPasswordChangeDoneView.as_view(), name='password_change_done'),
]