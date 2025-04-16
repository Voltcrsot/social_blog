# users/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
# Добавляем ListView для списков подписчиков/подписок
from django.views.generic import DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
# Добавляем стандартные views для паролей
from django.contrib.auth import get_user_model, authenticate, login, logout, views as auth_views
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
# Добавляем Http404 для ProfileDetailView и HttpResponseRedirect для login/register
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.template.loader import render_to_string
from django.contrib import messages
from django.utils import timezone

# Импорты моделей
from .models import Profile
# Добавляем Category и Prefetch для оптимизации
from posts.models import Post, Vote, Category, Comment
from django.db.models import Count, Q, Prefetch # Убедимся, что Prefetch импортирован
from django.contrib.contenttypes.models import ContentType

# Импортируем наши формы
from .forms import UserUpdateForm, ProfileUpdateForm, UserLoginForm, UserRegistrationForm
# Добавляем формы для сброса пароля, если хотим их кастомизировать
# from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm

User = get_user_model()

# --- Представления аутентификации (оставляем как есть) ---

@require_http_methods(["GET", "POST"])
def user_register_view(request): # Переименовал для ясности
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Регистрация прошла успешно! Теперь вы можете войти.")
            return redirect(reverse('users:login'))
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме регистрации.")
    else:
        form = UserRegistrationForm()
    context = {
        'form': form,
        'title': 'Регистрация'
    }
    return render(request, 'users/register.html', context)

@require_http_methods(["GET", "POST"])
def user_login_view(request): # Переименовал для ясности
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            next_url = request.POST.get('next', '/')
            return redirect(next_url or '/')
        else:
            messages.error(request, "Неверное имя пользователя/email или пароль.")
    else:
        form = UserLoginForm(request)
    context = {
        'form': form,
        'title': 'Вход',
        'next': request.GET.get('next', '/')
    }
    return render(request, 'users/login.html', context)

@login_required
def user_logout_view(request): # Переименовал для ясности
    logout(request)
    messages.info(request, "Вы успешно вышли из системы.")
    return redirect('/')


# --- Просмотр профиля (добавим prefetch_related для постов) ---
class ProfileDetailView(DetailView):
    model = Profile
    template_name = 'users/profile_detail.html'
    context_object_name = 'profile'
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    def get_queryset(self):
        # Оптимизация: выбираем пользователя и предзагружаем подписки/подписчиков
        # чтобы избежать N+1 запросов при подсчете в шаблоне или методах модели
        return Profile.objects.select_related('user').prefetch_related(
            'following', # Предзагрузка тех, на кого подписан
            'followers'  # Предзагрузка подписчиков
        ).all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object # Профиль, который просматриваем
        viewing_user = self.request.user # Пользователь, который смотрит

        # Статус подписки и возможность подписки
        is_following = False
        can_follow = False
        if viewing_user.is_authenticated and viewing_user != profile.user:
            can_follow = True
            if hasattr(viewing_user, 'profile'):
                # Используем предзагруженные данные, если возможно
                # Вместо is_following(profile) можно проверить наличие profile в viewing_user.profile.following.all()
                # Но метод is_following более читаем, оставим его.
                is_following = viewing_user.profile.is_following(profile)

        context['is_following'] = is_following
        context['can_follow'] = can_follow
        context['requesting_user'] = viewing_user # Явно передаем для шаблона кнопки

        # Загрузка и фильтрация постов
        # Вынесем логику фильтрации видимых постов в менеджер модели Post
        user_posts_qs = Post.objects.filter(author=profile.user).select_related('category', 'author__profile')
        # Предполагаем, что у Post.objects есть метод get_visible_posts_for_user
        # Если его нет, нужно добавить в posts/models.py (см. предыдущий ответ)
        try:
            visible_posts = Post.objects.get_visible_posts_for_user(
                user=viewing_user,
                base_queryset=user_posts_qs
            )
        except AttributeError:
             # Если метода нет, возвращаем только публичные посты (упрощенная логика)
             visible_posts = user_posts_qs.filter(is_published=True, published_at__lte=timezone.now(), visibility=Post.VISIBILITY_PUBLIC)
             messages.warning(self.request, "Ошибка: не найден метод get_visible_posts_for_user. Отображаются только публичные посты.")


        posts_with_counts = visible_posts.annotate(
            likes_count=Count('votes', filter=Q(votes__vote_type=Vote.LIKE), distinct=True),
            dislikes_count=Count('votes', filter=Q(votes__vote_type=Vote.DISLIKE), distinct=True),
            comments_count=Count('comments', distinct=True)
        ).order_by('-published_at', '-created_at')

        context['posts'] = posts_with_counts

        # Голоса текущего пользователя
        user_votes = {}
        visible_post_ids = [post.id for post in posts_with_counts]
        if viewing_user.is_authenticated and visible_post_ids:
            content_type = ContentType.objects.get_for_model(Post)
            votes = Vote.objects.filter(
                user=viewing_user, content_type=content_type, object_id__in=visible_post_ids
            ).values('object_id', 'vote_type')
            user_votes = {vote['object_id']: vote['vote_type'] for vote in votes}
        context['user_votes'] = user_votes

        context['title'] = f'Профиль {profile.user.username}'
        context['category'] = None
        return context


# --- Редактирование профиля (оставляем как есть) ---
@method_decorator(login_required, name='dispatch')
class ProfileUpdateView(View):
    user_form_class = UserUpdateForm
    profile_form_class = ProfileUpdateForm
    template_name = 'users/profile_edit.html'

    def get_object(self):
        # Профиль должен существовать благодаря сигналу
        return get_object_or_404(Profile, user=self.request.user)

    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        user_form = self.user_form_class(instance=request.user)
        profile_form = self.profile_form_class(instance=profile)
        return render(request, self.template_name, self._get_context(user_form, profile_form))

    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        user_form = self.user_form_class(request.POST, instance=request.user)
        profile_form = self.profile_form_class(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect(reverse('users:profile_edit'))
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
            return render(request, self.template_name, self._get_context(user_form, profile_form))

    def _get_context(self, user_form, profile_form):
        return {
            'title': 'Редактирование профиля',
            'user_form': user_form,
            'profile_form': profile_form,
            # 'user_email': self.request.user.email # Можно убрать, если не используется
        }


# --- toggle_follow (УЛУЧШЕНО с OOB) ---
@login_required
@require_POST
def toggle_follow_view(request, username): # Переименовал для ясности
    user_to_toggle = get_object_or_404(User, username=username)
    profile_to_toggle = get_object_or_404(Profile, user=user_to_toggle)
    requesting_user = request.user

    try:
        requesting_user_profile = requesting_user.profile
    except Profile.DoesNotExist:
         messages.error(request, "Произошла ошибка: ваш профиль не найден.")
         # Лучше вернуть ошибку для HTMX, чем редирект
         return HttpResponse("Ошибка профиля", status=403) # Forbidden

    if requesting_user_profile == profile_to_toggle:
        messages.warning(request, "Вы не можете подписаться на самого себя.")
        return HttpResponse("Нельзя подписаться на себя", status=403) # Forbidden

    is_currently_following = requesting_user_profile.is_following(profile_to_toggle)
    new_following_status = False # Статус после выполнения действия

    if is_currently_following:
        requesting_user_profile.unfollow(profile_to_toggle)
        new_following_status = False
    else:
        requesting_user_profile.follow(profile_to_toggle)
        new_following_status = True

    # --- Подготовка контекста для рендеринга фрагментов ---
    button_context = {
        'profile': profile_to_toggle,
        'is_following': new_following_status,
        'can_follow': True, # Т.к. мы прошли проверки
        'requesting_user': requesting_user
    }
    button_html = render_to_string(
        'users/partials/follow_button_fragment.html', # Фрагмент кнопки
        button_context,
        request=request
    )

    # --- Получаем ОБНОВЛЕННЫЕ счетчики ---
    # Нужен refresh_from_db, чтобы получить актуальные M2M счетчики
    profile_to_toggle.refresh_from_db()
    requesting_user_profile.refresh_from_db()

    # Счетчики профиля, на который/с которого подписались
    followers_count_html = f'<span id="followers-count-{profile_to_toggle.user.username}">{profile_to_toggle.followers.count()}</span>'
    # Счетчики профиля, который подписался/отписался
    following_count_html = f'<span id="following-count-{requesting_user_profile.user.username}">{requesting_user_profile.following.count()}</span>'

    # --- Собираем OOB Swap ответ ---
    # Основной ответ - это кнопка (для hx-swap="outerHTML" по умолчанию)
    response = HttpResponse(button_html)
    # Добавляем OOB для счетчиков
    response['HX-Swap-Oob'] = (
        f'innerHTML:#followers-count-{profile_to_toggle.user.username}:{followers_count_html},'
        # Обновляем счетчик Подписчиков на странице профиля profile_to_toggle
        # Обновление счетчика "Подписки" для requesting_user не нужно,
        # т.к. мы обычно находимся на странице другого пользователя.
        # Если бы кнопка была в хедере или на своей странице, то добавили бы:
        # f'innerHTML:#following-count-{requesting_user_profile.user.username}:{following_count_html}'
    )

    return response


# --- Списки подписчиков/подписок (НОВЫЕ ПРЕДСТАВЛЕНИЯ) ---

class FollowingListView(ListView):
    """Отображает список пользователей, на которых подписан указанный пользователь."""
    model = Profile
    template_name = 'users/follow_list.html'
    context_object_name = 'profile_list'
    paginate_by = 20

    def get_queryset(self):
        username = self.kwargs.get('username')
        # Оптимизируем: сразу получаем пользователя и его подписки
        owner_profile = get_object_or_404(
            Profile.objects.select_related('user').prefetch_related('following__user'), # Предзагружаем пользователей, на которых подписаны
            user__username=username
        )
        self.owner_profile = owner_profile
        return owner_profile.following.order_by('user__username') # Сортируем по имени пользователя

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner_profile'] = self.owner_profile
        context['title'] = f"Подписки {self.owner_profile.user.username}"
        context['list_type'] = 'following'

        # Статусы подписки ТЕКУЩЕГО пользователя на профили в списке
        following_status = {}
        current_user = self.request.user
        if current_user.is_authenticated and hasattr(current_user, 'profile'):
            # Получаем PK профилей из текущей страницы пагинации
            profile_pks_in_list = [p.pk for p in context['profile_list']]
            if profile_pks_in_list:
                # Узнаем, на кого из них подписан текущий пользователь
                following_pks = current_user.profile.following.filter(
                    pk__in=profile_pks_in_list
                ).values_list('pk', flat=True)
                # Создаем словарь {profile_pk: True} для удобной проверки в шаблоне
                following_status = {pk: True for pk in following_pks}
        context['current_user_following_status'] = following_status

        return context

class FollowersListView(ListView):
    """Отображает список пользователей, которые подписаны на указанного пользователя."""
    model = Profile
    template_name = 'users/follow_list.html'
    context_object_name = 'profile_list'
    paginate_by = 20

    def get_queryset(self):
        username = self.kwargs.get('username')
        # Оптимизируем: сразу получаем пользователя и его подписчиков
        owner_profile = get_object_or_404(
            Profile.objects.select_related('user').prefetch_related('followers__user'), # Предзагружаем пользователей-подписчиков
            user__username=username
        )
        self.owner_profile = owner_profile
        return owner_profile.followers.order_by('user__username') # Сортируем по имени пользователя

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['owner_profile'] = self.owner_profile
        context['title'] = f"Подписчики {self.owner_profile.user.username}"
        context['list_type'] = 'followers'

        # Статусы подписки ТЕКУЩЕГО пользователя на профили в списке
        following_status = {}
        current_user = self.request.user
        if current_user.is_authenticated and hasattr(current_user, 'profile'):
            profile_pks_in_list = [p.pk for p in context['profile_list']]
            if profile_pks_in_list:
                following_pks = current_user.profile.following.filter(
                    pk__in=profile_pks_in_list
                ).values_list('pk', flat=True)
                following_status = {pk: True for pk in following_pks}
        context['current_user_following_status'] = following_status

        return context


# --- Представления для сброса/изменения пароля (НОВЫЕ, используют стандартные) ---

class UserPasswordResetView(auth_views.PasswordResetView):
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')
    # from_email = 'your_email@example.com' # Можно указать email отправителя

class UserPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

class UserPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')

class UserPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'

# Изменение пароля для залогиненного юзера
class UserPasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = 'users/password_change_form.html'
    success_url = reverse_lazy('users:password_change_done')

class UserPasswordChangeDoneView(LoginRequiredMixin, auth_views.PasswordChangeDoneView):
    template_name = 'users/password_change_done.html'