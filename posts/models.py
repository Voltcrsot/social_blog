# posts/models.py

import secrets
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, Manager
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
# slugify больше не нужен для генерации основного слага, но может быть полезен для Category
from django.utils.text import slugify

# --- Менеджеры и Категория остаются без изменений ---
class PostManager(Manager):
    def get_queryset(self): return super().get_queryset()
    def published(self):
        now = timezone.now()
        return self.get_queryset().filter(is_published=True, published_at__lte=now)
    def get_visible_posts_for_user(self, user, base_queryset=None):
        now = timezone.now()
        published_q = Q(is_published=True, published_at__lte=now)
        if base_queryset is None: qs = self.get_queryset()
        else: qs = base_queryset
        if user and user.is_authenticated:
            visibility_q = Q(visibility=Post.VISIBILITY_PUBLIC)
            visibility_q |= Q(visibility=Post.VISIBILITY_PRIVATE, author=user)
            if hasattr(user, 'profile'):
                visibility_q |= Q(visibility=Post.VISIBILITY_FOLLOWERS, author__profile__followers=user.profile)
            draft_q = Q(author=user) & (Q(is_published=False) | Q(published_at__gt=now))
            final_q = (published_q & visibility_q) | draft_q
        else:
            final_q = published_q & Q(visibility=Post.VISIBILITY_PUBLIC)
        return qs.filter(final_q).distinct()

class Category(models.Model):
    name = models.CharField("Название", max_length=100, unique=True, help_text="Максимум 100 символов.")
    slug = models.SlugField("Слаг", max_length=120, unique=True, help_text="Уникальный фрагмент URL на основе названия. Максимум 120 символов.")
    class Meta: verbose_name = "Категория"; verbose_name_plural = "Категории"; ordering = ["name"]
    def __str__(self): return self.name
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)
    def get_absolute_url(self): return reverse("posts:post_list_by_category", args=[self.slug])


# --- Модель Post ---
class Post(models.Model):
    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_FOLLOWERS = 'followers'
    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, 'Всем'),
        (VISIBILITY_FOLLOWERS, 'Только подписчикам'),
        (VISIBILITY_PRIVATE, 'Только мне'),
    ]

    title = models.CharField("Заголовок", max_length=200, help_text="Максимум 200 символов.")
    # Слаг остается NOT NULL и unique
    slug = models.SlugField(
        "Слаг",
        max_length=220, # Оставим длину, хотя случайные короче
        unique=True,
        help_text="Уникальный случайный идентификатор URL.", # Обновили help_text
    )
    content = models.TextField("Содержимое")
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="posts",verbose_name="Автор")
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True,related_name="posts",verbose_name="Категория")
    visibility = models.CharField("Видимость", max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PUBLIC, db_index=True, help_text="Кто сможет видеть пост после публикации.")
    is_published = models.BooleanField("Опубликовано", default=False, help_text="Пост будет виден согласно настройкам видимости и даты публикации.")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    published_at = models.DateTimeField("Дата публикации", null=True, blank=True, db_index=True, help_text="Дата и время, когда пост станет доступен (если отмечено 'Опубликовано'). Если пусто, используется текущее время.")
    votes = GenericRelation("Vote", related_query_name="post_votes")

    objects = PostManager()

    class Meta:
        verbose_name = "Пост"; verbose_name_plural = "Посты"; ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["-published_at", "-created_at"]),
            models.Index(fields=["author"]), models.Index(fields=["category"]),
            models.Index(fields=["visibility"]), models.Index(fields=["is_published", "published_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self): return self.title

    # --- ИЗМЕНЕНО: Метод save() ВСЕГДА генерирует случайный слаг при создании ---
    def save(self, *args, **kwargs):
        # Генерируем слаг только если он еще не задан (т.е. при создании поста)
        if not self.slug:
            queryset = Post.objects.all()
            # Исключаем себя при редактировании (хотя этот блок теперь только для создания)
            # if self.pk:
            #     queryset = queryset.exclude(pk=self.pk)

            # Генерируем случайный слаг и проверяем уникальность
            while True:
                # Генерируем URL-безопасную строку, например, из 12 байт (~16 символов)
                # Можно изменить длину, если нужно (например, 8 байт ~ 11 символов)
                candidate_slug = secrets.token_urlsafe(12)
                if not queryset.filter(slug=candidate_slug).exists():
                    self.slug = candidate_slug
                    break # Выходим, как только нашли уникальный

        # --- Логика установки/сброса published_at и visibility (остается как есть) ---
        if self.is_published:
            if self.published_at is None:
                self.published_at = timezone.now()
        else:
            self.published_at = None
            self.visibility = self.VISIBILITY_PRIVATE
        # -------------------------------------------------------------------

        super().save(*args, **kwargs) # Сохраняем объект с уже присвоенным слагом
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    def get_absolute_url(self):
        # URL строится на основе слага
        if self.slug:
            try:
                return reverse("posts:post_detail", args=[self.slug])
            except NoReverseMatch:
                print(f"Warning: NoReverseMatch for slug '{self.slug}' in post ID {self.id}")
                return reverse("posts:post_list")
        else:
            print(f"Error: Post ID {self.id} has no slug! Falling back to post_list.")
            return reverse("posts:post_list")

    @property
    def total_votes(self):
        result = self.votes.aggregate(total=models.Sum("vote_type"))
        return result.get("total") or 0

    def can_view(self, user):
        # (Логика can_view остается без изменений)
        is_draft = not self.is_published or (self.published_at and self.published_at > timezone.now())
        if is_draft:
            return user.is_authenticated and user == self.author
        if self.visibility == self.VISIBILITY_PUBLIC:
            return True
        if not user or not user.is_authenticated:
            return False
        if self.visibility == self.VISIBILITY_PRIVATE:
            return user == self.author
        if self.visibility == self.VISIBILITY_FOLLOWERS:
            if user == self.author: return True
            if hasattr(user, 'profile') and hasattr(self.author, 'profile'):
                return self.author.profile.followers.filter(pk=user.profile.pk).exists()
            return False
        return False


# --- Модель Comment ---
# (остается без изменений)
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments", verbose_name="Пост")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments", verbose_name="Автор")
    content = models.TextField("Текст комментария")
    created_at = models.DateTimeField("Создано", auto_now_add=True, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies", verbose_name="Родительский комментарий")
    class Meta: verbose_name = "Комментарий"; verbose_name_plural = "Комментарии"; ordering = ["created_at"]
    def __str__(self): return f'Комментарий от {self.author} к "{self.post.title[:30]}..."'
    @property
    def is_parent(self): return self.parent is None

# --- Модель Vote ---
# (остается без изменений)
class Vote(models.Model):
    LIKE = 1; DISLIKE = -1
    VOTE_CHOICES = ((LIKE, "Нравится"), (DISLIKE, "Не нравится"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes", verbose_name="Пользователь")
    vote_type = models.SmallIntegerField("Тип голоса", choices=VOTE_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Тип контента")
    object_id = models.PositiveIntegerField("ID объекта")
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    class Meta:
        verbose_name = "Голос"; verbose_name_plural = "Голоса"
        constraints = [models.UniqueConstraint(fields=["user", "content_type", "object_id"], name="unique_user_content_vote")]
        indexes = [models.Index(fields=["content_type", "object_id"])]
    def __str__(self):
        try: content_repr = str(self.content_object) if self.content_object else "Объект удален"
        except Exception: content_repr = f"Объект ({self.content_type} ID: {self.object_id})"
        return f"{self.user} - {self.get_vote_type_display()} ({content_repr})"