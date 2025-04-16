# users/templatetags/user_tags.py

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Позволяет получить значение из словаря по ключу в шаблоне Django.
    Использование: {{ my_dictionary|get_item:my_key }}
    Возвращает None, если ключ не найден.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None # Или можно вернуть пустую строку '' или 0 в зависимости от контекста

# Можно добавить другие теги или фильтры для приложения users здесь, если понадобятся.