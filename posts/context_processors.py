# posts/context_processors.py
from .models import Category, Post # Импортируем модели из текущего приложения
from django.db.models import Count, Q
from django.utils import timezone

def categories_processor(request):
    """
    Добавляет список активных категорий (с опубликованными постами)
    в контекст всех шаблонов.
    """
    # Аннотируем количество опубликованных постов для каждой категории
    categories = Category.objects.annotate(
        num_posts=Count('posts', filter=Q(posts__is_published=True, posts__published_at__lte=timezone.now()))
    ).filter(num_posts__gt=0).order_by('name') # Берем только категории, где есть посты

    # Возвращаем словарь, который будет добавлен в общий контекст шаблонов
    return {'all_categories': categories}