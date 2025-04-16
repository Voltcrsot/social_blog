# posts/admin.py

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone # Импортируем timezone

from .models import Category, Comment, Post, Vote

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Кол-во постов', ordering='posts_count')
    def post_count(self, obj):
        return obj.posts_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Считаем опубликованные посты, время которых наступило
        queryset = queryset.annotate(
            posts_count=Count('posts', filter=Q(posts__is_published=True, posts__published_at__lte=timezone.now()))
        )
        return queryset

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('author', 'created_at')
    fields = ('author', 'content', 'created_at', 'parent')
    ordering = ('created_at',)
    autocomplete_fields = ['author', 'parent']
    verbose_name = "Комментарий"
    verbose_name_plural = "Комментарии"

class VoteInline(GenericTabularInline):
    model = Vote
    extra = 0
    readonly_fields = ('user', 'vote_type', 'created_at')
    fields = ('user', 'vote_type', 'created_at')
    verbose_name = "Голос"
    verbose_name_plural = "Голоса"

    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'author_link',
        'category_link',
        'visibility', # Отображаем видимость
        'is_published',
        'published_at',
        'display_vote_count',
        'comment_count',
    )
    # Добавляем visibility в фильтр
    list_filter = ('is_published', 'visibility', 'category', 'author', 'created_at', 'published_at')
    search_fields = ('title', 'content', 'author__username', 'category__name')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ('-published_at', '-created_at')
    readonly_fields = ('created_at',)
    list_select_related = ('author', 'category')
    autocomplete_fields = ['author', 'category']

    # Указываем поля для формы редактирования поста в админке
    # Убираем is_published и published_at, т.к. они теперь управляются формой PostForm
    # (хотя в админке стандартная ModelForm, не PostForm, поэтому можно вернуть для прямого управления)
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'author', 'content', 'category', 'visibility')}), # Добавили visibility
        ('Статус и время', {'fields': ('is_published', 'published_at', 'created_at')}), # Добавили created_at (readonly)
    )
    inlines = [CommentInline, VoteInline]

    @admin.display(description='Автор', ordering='author__username')
    def author_link(self, obj):
        if obj.author:
            url = reverse('admin:auth_user_change', args=[obj.author.pk])
            return format_html('<a href="{}">{}</a>', url, obj.author.username)
        return "-"

    @admin.display(description='Категория', ordering='category__name')
    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:posts_category_change', args=[obj.category.pk])
            return format_html('<a href="{}">{}</a>', url, obj.category.name)
        return "-"

    @admin.display(description='Голоса (Л/Д)', ordering='likes_count')
    def display_vote_count(self, obj):
        return f"{getattr(obj, 'likes_count', 0)} / {getattr(obj, 'dislikes_count', 0)}"

    @admin.display(description='Комм.', ordering='comments_count')
    def comment_count(self, obj):
        return getattr(obj, 'comments_count', 0)

    # Убираем save_formset, так как автор для инлайн-комментариев не нужен
    # (в админке комментарии может добавлять только админ)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('author', 'category')
        queryset = queryset.annotate(
            likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
            dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
            comments_count=Count('comments', distinct=True),
        )
        return queryset

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_link', 'post_link', 'content_preview', 'created_at', 'parent_link')
    list_filter = ('created_at', 'author')
    search_fields = ('content', 'post__title', 'author__username', 'parent__author__username')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['post', 'author', 'parent']
    list_select_related = ('author', 'post', 'parent')

    @admin.display(description='Автор', ordering='author__username')
    def author_link(self, obj):
        if obj.author:
            url = reverse('admin:auth_user_change', args=[obj.author.pk])
            return format_html('<a href="{}">{}</a>', url, obj.author.username)
        return "-"

    @admin.display(description='Пост', ordering='post__title')
    def post_link(self, obj):
        if obj.post:
            url = reverse('admin:posts_post_change', args=[obj.post.pk])
            return format_html('<a href="{}">{}</a>', url, obj.post.title)
        return "Пост удален" # Если пост удален

    @admin.display(description='Текст')
    def content_preview(self, obj):
        max_len = 50
        if obj.content:
            return (obj.content[:max_len] + '...') if len(obj.content) > max_len else obj.content
        return "-"

    @admin.display(description='Родитель', ordering='parent__created_at')
    def parent_link(self, obj):
        if obj.parent:
            url = reverse('admin:posts_comment_change', args=[obj.parent.pk])
            return format_html('<a href="{}">Комм. #{}</a>', url, obj.parent.pk)
        return "-"

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'vote_type', 'content_object_link', 'created_at')
    list_filter = ('vote_type', 'created_at', 'content_type')
    search_fields = ('user__username', 'content_type__model')
    readonly_fields = ('user', 'vote_type', 'content_type', 'object_id', 'content_object', 'created_at')
    list_select_related = ('user', 'content_type')

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

    @admin.display(description='Пользователь', ordering='user__username')
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"

    @admin.display(description='Объект')
    def content_object_link(self, obj):
        if obj.content_object:
            try:
                admin_url = reverse(
                    f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                    args=[obj.object_id]
                )
                model_name = obj.content_type.model.capitalize()
                return format_html('<a href="{}">{} #{} ({})</a>', admin_url, model_name, obj.object_id, obj.content_object)
            except Exception:
                 model_name = obj.content_type.model.capitalize()
                 return f"{model_name} #{obj.object_id} ({obj.content_object})"
        return "Объект удален"