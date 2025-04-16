# posts/templatetags/post_tags.py
from django import template
from django.utils.http import urlencode

register = template.Library()

@register.filter(name='get_item') # Явно указываем имя фильтра
def get_item(dictionary, key):
    """Позволяет получить значение из словаря по ключу в шаблоне."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None # Возвращаем None, если это не словарь или ключа нет

@register.filter(name='urlencode_partial') # Явно указываем имя фильтра
def urlencode_partial(get_params, exclude_key=""):
    """Кодирует GET-параметры, исключая указанный ключ."""
    params = get_params.copy()
    if exclude_key and exclude_key in params:
        params.pop(exclude_key)
    if params:
        return f"&{urlencode(params)}"
    return ""