# posts/components/comment_item/comment_item.py
from django_components import component

@component.register("comment_item")
class CommentDisplay(component.Component):
    template_name = "comment_item/comment_item.html"

    # Контекст передается извне
    def get_context_data(self, comment, user):
        return {"comment": comment, "user": user}