# posts/urls.py
from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    # --- Списки постов ---
    path('feed/', views.PostFeedView.as_view(), name='post_feed'),
    path('category/<slug:category_slug>/', views.PostListView.as_view(), name='post_list_by_category'),

    # --- CRUD постов ---
    path('post/new/', views.PostCreateView.as_view(), name='post_create'),
    path('<slug:slug>/edit/', views.PostUpdateView.as_view(), name='post_edit'), # Редактирование идет до деталей
    path('<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),    # Детали поста

    # --- HTMX для постов ---
    path('post/<int:post_id>/vote/', views.post_vote, name='post_vote'),
    path('post/<int:post_id>/comment/add/', views.add_comment, name='add_comment'),

    # --- HTMX для комментариев ---
    path('comment/<int:comment_id>/reply/', views.get_reply_form, name='get_reply_form'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('comment/<int:comment_id>/edit/', views.get_edit_form, name='get_edit_form'),
    path('comment/<int:comment_id>/update/', views.update_comment, name='update_comment'),
    path('comment/<int:comment_id>/content/', views.get_comment_content, name='get_comment_content'),

    # --- Главная страница (список всех постов) ---
    path('', views.PostListView.as_view(), name='post_list'), # Идет последней
]