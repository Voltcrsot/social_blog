# posts/components/post_actions/post_actions.py
from django_components import component

@component.register("post_actions")
class PostActions(component.Component):
    template_name = "post_actions/post_actions.html"

    # Передаем post и user_vote извне
    def get_context_data(self, post, user_vote=None):
        return {"post": post, "user_vote": user_vote}