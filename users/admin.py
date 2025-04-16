# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Profile # Импортируем Profile

# Отменяем регистрацию стандартной UserAdmin, чтобы добавить инлайн
admin.site.unregister(User)

class ProfileInline(admin.StackedInline):
    """Встраиваемая форма для профиля на странице пользователя."""
    model = Profile
    can_delete = False
    verbose_name = "Профиль пользователя"
    verbose_name_plural = "Профиль пользователя"
    fk_name = 'user'
    fields = ('bio', 'avatar') # Поля для инлайн-редактирования

@admin.register(User) # Регистрируем User с нашим UserAdmin
class UserAdmin(BaseUserAdmin):
    """Кастомная админка для User, включающая Profile."""
    inlines = (ProfileInline,) # Добавляем инлайн
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
        'profile_link',
    )
    list_select_related = ('profile',) # Оптимизация
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups') # Стандартные фильтры
    search_fields = ('username', 'first_name', 'last_name', 'email', 'profile__bio') # Добавляем поиск по био

    @admin.display(description='Профиль', ordering='profile')
    def profile_link(self, obj):
        """Ссылка на страницу профиля в админке."""
        if hasattr(obj, 'profile') and obj.profile.pk:
            url = reverse('admin:users_profile_change', args=[obj.profile.pk])
            return format_html('<a href="{}">Профиль #{}</a>', url, obj.profile.pk)
        return "-" # Возвращаем дефис, если профиля нет

    # Метод для подстраховки создания профиля (хотя сигнал должен справляться)
    def get_inline_instances(self, request, obj=None):
        if obj:
            Profile.objects.get_or_create(user=obj)
        return super().get_inline_instances(request, obj)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Отдельная админка для Профилей."""
    list_display = ('user_link', 'bio_preview', 'following_count_display', 'followers_count_display')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'bio')
    list_select_related = ('user',)
    filter_horizontal = ('following',)
    readonly_fields = ('following_count_display', 'followers_count_display')
    autocomplete_fields = ['user', 'following']

    fieldsets = (
        (None, {'fields': ('user',)}),
        ('Информация', {'fields': ('bio', 'avatar')}),
        ('Подписки', {'fields': ('following', 'following_count_display', 'followers_count_display')}),
    )

    @admin.display(description='Пользователь', ordering='user__username')
    def user_link(self, obj):
        """Ссылка на пользователя."""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "Пользователь удален" # Если user удален (маловероятно из-за CASCADE)

    @admin.display(description='Био')
    def bio_preview(self, obj):
        """Показывает начало био."""
        max_len = 70
        if obj.bio:
            return (obj.bio[:max_len] + '...') if len(obj.bio) > max_len else obj.bio
        return "-"

    @admin.display(description='Подписок', ordering='num_following')
    def following_count_display(self, obj):
        return getattr(obj, 'num_following', 0) # Используем getattr с дефолтом 0

    @admin.display(description='Подписчиков', ordering='num_followers')
    def followers_count_display(self, obj):
        return getattr(obj, 'num_followers', 0) # Используем getattr с дефолтом 0

    def get_queryset(self, request):
        """Оптимизация: добавляем подсчет подписок."""
        queryset = super().get_queryset(request).select_related('user')
        queryset = queryset.annotate(
            num_following=Count('following', distinct=True),
            num_followers=Count('followers', distinct=True),
        )
        return queryset