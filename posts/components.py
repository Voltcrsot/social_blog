# posts/components.py

from django_components import component

# --- КОМПОНЕНТ ДЛЯ КОММЕНТАРИЯ ---
@component.register("comment_item_component") # НОВОЕ ИМЯ РЕГИСТРАЦИИ
class CommentItem(component.Component):
    """Компонент для отображения одного комментария и его ответов."""
    # Укажите правильный путь к вашему HTML шаблону комментария
    template_name = "posts/components/comment_item/comment_item.html" # Пример пути

    def get_context_data(self, comment, user, level=0):
        return {"comment": comment, "user": user, "level": level}

# --- КОМПОНЕНТ ДЛЯ КАРТОЧКИ ПОСТА ---
@component.register("post_card")
class PostCard(component.Component):
    """Компонент для отображения карточки поста в списке."""
    # Укажите правильный путь к вашему HTML шаблону карточки
    template_name = "posts/components/post_card/post_card.html" # Пример пути

    def get_context_data(self, post, user_vote=None):
        # Передаем post и user_vote в контекст шаблона
        return {"post": post, "user_vote": user_vote}

# --- КОМПОНЕНТ ДЛЯ КНОПОК ДЕЙСТВИЙ ПОСТА (если используется) ---
# Если вы используете include для кнопок, этот компонент не нужен
# @component.register("post_actions")
# class PostActions(component.Component):
#     template_name = "posts/components/post_actions/post_actions.html" # Пример пути
#
#     def get_context_data(self, post, user_vote=None):
#         return {"post": post, "user_vote": user_vote}