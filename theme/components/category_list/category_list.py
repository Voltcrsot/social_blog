# theme/components/category_list/category_list.py

from django_components import component
from django.db.models import Count, Q
from django.utils import timezone
# Импортируем модель Category из приложения posts
from posts.models import Category

@component.register("category_list")
class CategoryList(component.Component):
    template_name = "category_list/category_list.html"

    def get_context_data(self, current_category=None):
        # Получаем все категории с опубликованными постами
        all_categories = Category.objects.annotate(
            num_posts=Count(
                'posts',
                filter=Q(posts__is_published=True, posts__published_at__lte=timezone.now())
            )
        ).filter(num_posts__gt=0).order_by('name')

        return {
            "all_categories": all_categories,
            "current_category": current_category, # Передаем текущую категорию извне
        }