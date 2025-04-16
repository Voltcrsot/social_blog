# posts/components/post_card/post_card.py
from django_components import component

@component.register("post_card")
class PostCard(component.Component):
    template_name = "post_card/post_card.html"

    # Контекст передается извне при вызове компонента
    def get_context_data(self, post, user_vote=None):
        return {"post": post, "user_vote": user_vote}