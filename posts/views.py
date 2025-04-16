# posts/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, Prefetch
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, HttpResponseNotAllowed, Http404,
                         HttpResponseRedirect)  # Добавили HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.views.generic import DetailView, ListView, CreateView, UpdateView
from django.contrib import messages

from .models import Category, Comment, Post, Vote
from .forms import CommentForm, PostForm


class PostCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания нового поста."""
    model = Post
    form_class = PostForm
    template_name = 'posts/post_form.html'

    # success_url НЕ указываем, будем использовать get_success_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = "Создание нового поста"
        context['submit_button_text'] = "Сохранить пост"
        return context

    # --- ИСПРАВЛЕННЫЙ form_valid ---
    def form_valid(self, form):
        # Устанавливаем автора перед сохранением
        form.instance.author = self.request.user
        # Явно сохраняем объект, чтобы вызвалcя Post.save() и сгенерировался slug
        self.object = form.save()
        messages.success(self.request, "Пост успешно создан!")
        # Возвращаем редирект на URL, полученный из get_success_url
        return HttpResponseRedirect(self.get_success_url())

    # --- КОНЕЦ ИСПРАВЛЕННОГО form_valid ---

    # --- ИСПРАВЛЕННЫЙ get_success_url ---
    def get_success_url(self):
        # Строим URL на детальную страницу созданного поста (self.object)
        # self.object уже сохранен и должен иметь slug
        try:
            # Используем kwargs для передачи slug
            url = reverse('posts:post_detail', kwargs={'slug': self.object.slug})
            return url
        except Exception as e:
            # Обработка возможной ошибки (например, если слаг пустой)
            print(f"ERROR generating success URL for post {self.object.id}: {e}")
            messages.warning(self.request, "Пост создан, но произошла ошибка при перенаправлении.")
            # Возвращаем URL списка постов как запасной вариант
            return reverse_lazy('posts:post_list')
    # --- КОНЕЦ ИСПРАВЛЕННОГО get_success_url ---


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования существующего поста."""
    model = Post
    form_class = PostForm
    template_name = 'posts/post_form.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Разрешаем редактировать только свои посты
        return super().get_queryset().filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Редактирование поста: {self.object.title}"
        context['submit_button_text'] = "Сохранить изменения"
        # Инициализация поля scheduled_at
        if self.object.published_at and self.object.published_at > timezone.now():
            context['form'].fields['scheduled_at'].initial = self.object.published_at.strftime('%Y-%m-%dT%H:%M')
        return context

    def form_valid(self, form):
        # Метод save модели Post (вызываемый из form.save()) должен обновить слаг, если заголовок изменился
        response = super().form_valid(form)
        messages.success(self.request, "Пост успешно обновлен!")
        return response

    def get_success_url(self):
        post = self.object
        # Убедимся, что у объекта есть слаг после сохранения
        if post.slug and post.can_view(self.request.user):
            # Используем kwargs для передачи slug
            return reverse('posts:post_detail', kwargs={'slug': post.slug})
        else:
            if not post.slug:
                messages.warning(self.request, "Не удалось сгенерировать URL для поста.")
            else:
                messages.info(self.request, "Пост сохранен, но вам он может быть не виден согласно настройкам.")
            return reverse_lazy('posts:post_list')


class PostListView(ListView):
    """Отображает список постов с учетом видимости и пагинацией."""
    model = Post
    template_name = 'posts/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        base_qs = Post.objects.select_related('author__profile', 'category')
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            base_qs = base_qs.filter(category=category)
            self.category = category
        else:
            self.category = None

        user = self.request.user
        now = timezone.now()
        published_q = Q(is_published=True, published_at__lte=now)

        if user.is_authenticated:
            visibility_q = Q(visibility=Post.VISIBILITY_PUBLIC) | \
                           Q(visibility=Post.VISIBILITY_PRIVATE, author=user)
            if hasattr(user, 'profile'):
                visibility_q |= Q(visibility=Post.VISIBILITY_FOLLOWERS, author__profile__followers=user.profile)
            author_draft_q = Q(author=user) & ~published_q
            final_q = (published_q & visibility_q) | author_draft_q
        else:
            final_q = published_q & Q(visibility=Post.VISIBILITY_PUBLIC)

        queryset = base_qs.filter(final_q).distinct()
        queryset = queryset.annotate(
            likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
            dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
            comments_count=Count('comments', distinct=True)
        )
        return queryset.order_by('-is_published', '-published_at', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = getattr(self, 'category', None)
        context['title'] = f'Посты категории "{self.category.name}"' if self.category else 'Все посты'
        user_votes = {}
        if self.request.user.is_authenticated:
            post_ids = [post.id for post in context['posts']]
            if post_ids:
                content_type = ContentType.objects.get_for_model(Post)
                votes = Vote.objects.filter(
                    user=self.request.user, content_type=content_type, object_id__in=post_ids
                ).values('object_id', 'vote_type')
                user_votes = {vote['object_id']: vote['vote_type'] for vote in votes}
        context['user_votes'] = user_votes
        return context


class PostDetailView(DetailView):
    """Отображает детальную страницу поста и его комментарии."""
    model = Post
    template_name = 'posts/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        queryset = self.get_queryset()
        obj = super().get_object(queryset=queryset)
        if not obj.can_view(self.request.user):
            raise Http404("Пост не найден или у вас нет прав на его просмотр.")
        return obj

    def get_queryset(self):
        return Post.objects.select_related(
            'author__profile', 'category'
        ).prefetch_related(
            Prefetch('comments', queryset=Comment.objects.select_related('author__profile').order_by('created_at'))
        ).annotate(
            likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
            dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
        ).filter(slug=self.kwargs.get(self.slug_url_kwarg))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        context['title'] = post.title
        context['comments'] = post.comments.all()

        user_vote = None
        if self.request.user.is_authenticated:
            content_type = ContentType.objects.get_for_model(Post)
            try:
                vote_obj = Vote.objects.get(user=self.request.user, content_type=content_type, object_id=post.id)
                user_vote = vote_obj.vote_type
            except Vote.DoesNotExist:
                pass
        context['user_vote'] = user_vote

        if self.request.user.is_authenticated:
            context['comment_form'] = CommentForm()
        return context


class PostFeedView(LoginRequiredMixin, ListView):
    """Отображает ленту постов от пользователей, на которых подписан текущий."""
    model = Post
    template_name = 'posts/post_feed.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        following_user_ids = []
        if hasattr(user, 'profile'):
            following_user_ids = user.profile.following.values_list('user_id', flat=True)
        if not following_user_ids:
            return Post.objects.none()
        queryset = Post.objects.filter(
            author_id__in=following_user_ids,
            is_published=True,
            published_at__lte=timezone.now(),
            visibility__in=[Post.VISIBILITY_PUBLIC, Post.VISIBILITY_FOLLOWERS]
        ).select_related('author__profile', 'category').annotate(
            likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
            dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
            comments_count=Count('comments', distinct=True)
        ).order_by('-published_at')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Моя лента'
        user_votes = {}
        post_ids = [post.id for post in context['posts']]
        if post_ids and self.request.user.is_authenticated:
            content_type = ContentType.objects.get_for_model(Post)
            votes = Vote.objects.filter(
                user=self.request.user, content_type=content_type, object_id__in=post_ids
            ).values('object_id', 'vote_type')
            user_votes = {vote['object_id']: vote['vote_type'] for vote in votes}
        context['user_votes'] = user_votes
        context['category'] = None
        return context


# --- HTMX Views ---

@login_required
@require_POST
def post_vote(request, post_id):
    """Обрабатывает лайк/дизлайк поста."""
    post = get_object_or_404(Post, pk=post_id)
    if not post.can_view(request.user):
        return HttpResponseForbidden("У вас нет доступа к этому посту для голосования.")
    vote_type = request.POST.get('vote_type')
    if vote_type not in ['like', 'dislike']: return HttpResponseBadRequest("Invalid vote type")
    vote_value = Vote.LIKE if vote_type == 'like' else Vote.DISLIKE
    content_type = ContentType.objects.get_for_model(Post)
    vote, created = Vote.objects.get_or_create(user=request.user, content_type=content_type, object_id=post.id,
                                               defaults={'vote_type': vote_value})
    user_vote_final_type = None
    if not created:
        if vote.vote_type == vote_value:
            vote.delete()
        else:
            vote.vote_type = vote_value; vote.save(); user_vote_final_type = vote_value
    else:
        user_vote_final_type = vote_value
    post_with_counts = Post.objects.filter(pk=post.id).annotate(
        likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
        dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
        comments_count=Count('comments', distinct=True)
    ).first()
    if not post_with_counts: return HttpResponseBadRequest("Post not found after voting.")
    context = {'post': post_with_counts, 'user_vote': user_vote_final_type, 'request': request}
    html_fragment = render_to_string('posts/partials/post_actions_fragment.html', context)
    return HttpResponse(html_fragment)


@login_required
@require_GET
def get_reply_form(request, comment_id):
    """Возвращает форму для ответа на комментарий."""
    parent_comment = get_object_or_404(Comment, pk=comment_id)
    if not parent_comment.post.can_view(request.user):
        return HttpResponseForbidden("Нет доступа к посту для ответа на комментарий.")
    form = CommentForm()
    context = {'form': form, 'parent_comment': parent_comment, 'post_id': parent_comment.post.id}
    return render(request, 'posts/partials/_comment_reply_form.html', context)


@login_required
@require_POST
def add_comment(request, post_id):
    """Добавляет новый комментарий или ответ."""
    post = get_object_or_404(Post, pk=post_id)
    if not post.can_view(request.user):
        return HttpResponseForbidden("Нет доступа к посту для добавления комментария.")
    form = CommentForm(request.POST)
    parent_comment = None
    parent_id = request.POST.get('parent_id')
    if parent_id:
        try:
            parent_comment = Comment.objects.get(pk=parent_id, post=post)
            level_check = 0;
            temp = parent_comment
            while temp:
                level_check += 1;
                temp = temp.parent
                if level_check > 5:  # Ограничение глубины ответа
                    return HttpResponseBadRequest("Нельзя отвечать на комментарий с таким уровнем вложенности.")
        except (Comment.DoesNotExist, ValueError):
            return HttpResponseBadRequest("Родительский комментарий не найден или ID некорректен.")

    if form.is_valid():
        new_comment = form.save(commit=False)
        new_comment.post = post
        new_comment.author = request.user
        new_comment.parent = parent_comment
        new_comment.save()
        level = 0
        if parent_comment:
            temp_parent = parent_comment
            while temp_parent: level += 1; temp_parent = temp_parent.parent
        context = {'comment': new_comment, 'user': request.user, 'level': level}
        try:
            template_path = 'posts/components/comment_display/comment_display.html'
            html_fragment = render_to_string(template_path, context, request=request)
        except Exception as e:
            print(f"Error rendering comment template ({template_path}): {e}")
            return HttpResponseBadRequest(f"Ошибка рендеринга комментария: {e}")
        if new_comment.parent_id:
            response = HttpResponse(status=204)  # No Content
            response['HX-Swap-Oob'] = f'beforeend:#replies-for-{new_comment.parent_id}:{html_fragment}'
            response['HX-Trigger-After-Swap'] = '{"commentAdded":true, "removeNoCommentsPlaceholder":""}'
        else:
            response = HttpResponse(html_fragment)
            if post.comments.filter(parent__isnull=True).count() == 1:
                response['HX-Swap-Oob'] = 'delete:#no-comments-placeholder'
            response['HX-Trigger-After-Swap'] = '{"commentAdded":true}'
        return response
    else:
        errors_str = "; ".join([f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()])
        messages.error(request, f"Ошибка валидации комментария: {errors_str}")
        return HttpResponseBadRequest(
            f"Ошибка валидации: {errors_str}" if errors_str else "Ошибка валидации комментария.")


@login_required
@require_http_methods(["DELETE"])
def delete_comment(request, comment_id):
    """Удаляет комментарий."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        return HttpResponseForbidden("Вы не можете удалить этот комментарий.")
    post_id = comment.post.id
    was_top_level = comment.parent is None
    comment.delete()
    response = HttpResponse(status=200)  # OK
    if was_top_level and not Comment.objects.filter(post_id=post_id, parent__isnull=True).exists():
        placeholder_html = '<p id="no-comments-placeholder" class="text-gray-500">Комментариев пока нет.</p>'
        response['HX-Swap-Oob'] = f'innerHTML:#comment-list:{placeholder_html}'
    response['HX-Trigger'] = '{"showMessage": "Комментарий удален"}'
    return response


@login_required
@require_GET
def get_edit_form(request, comment_id):
    """Возвращает форму для редактирования комментария."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        return HttpResponseForbidden("Вы не можете редактировать этот комментарий.")
    form = CommentForm(instance=comment)  # Предзаполняем форму
    context = {'form': form, 'comment': comment}
    return render(request, 'posts/partials/_comment_edit_form.html', context)


@login_required
@require_POST
def update_comment(request, comment_id):
    """Обновляет текст комментария."""
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        return HttpResponseForbidden("Вы не можете редактировать этот комментарий.")
    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        updated_comment = form.save()
        level = 0
        temp_parent = updated_comment.parent
        while temp_parent: level += 1; temp_parent = temp_parent.parent
        context = {'comment': updated_comment, 'user': request.user, 'level': level}
        template_path = 'posts/components/comment_display/comment_display.html'
        return render(request, template_path, context)
    else:
        context = {'form': form, 'comment': comment}
        response = render(request, 'posts/partials/_comment_edit_form.html', context)
        response['HX-Retarget'] = f'#comment-content-area-{comment.id} form'
        response['HX-Reswap'] = 'outerHTML'
        response.status_code = 400
        return response


@login_required
@require_GET
def get_comment_content(request, comment_id):
    """Возвращает HTML-блок с оригинальным текстом комментария."""
    comment = get_object_or_404(Comment, pk=comment_id)
    html_content = f'<div id="comment-content-{comment.id}" class="text-sm text-gray-700 whitespace-pre-wrap break-words mb-2">{comment.content}</div>'
    return HttpResponse(html_content)
