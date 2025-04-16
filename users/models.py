# users/models.py

# Убираем импорты, связанные с EmailVerificationCode
# import secrets # Больше не нужен
# from datetime import timedelta # Больше не нужен
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь")
    bio = models.TextField("О себе", blank=True)
    avatar = models.ImageField("Аватар", upload_to="avatars/", blank=True, null=True, help_text="Загрузите изображение профиля.")
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True, verbose_name="Подписки")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"
        # Убрали ordering, если не нужен специфичный порядок для профилей

    def __str__(self):
        return f'Профиль {self.user.username}'

    def get_absolute_url(self):
        """Возвращает URL для просмотра профиля пользователя."""
        return reverse('users:profile_detail', args=[self.user.username])

    # Опционально: методы для управления подписками
    def follow(self, profile_to_follow):
        """Подписаться на профиль."""
        if profile_to_follow not in self.following.all():
            self.following.add(profile_to_follow)
            return True
        return False

    def unfollow(self, profile_to_unfollow):
        """Отписаться от профиля."""
        if profile_to_unfollow in self.following.all():
            self.following.remove(profile_to_unfollow)
            return True
        return False

    def is_following(self, profile_to_check):
        """Проверяет, подписан ли текущий профиль на другой."""
        return self.following.filter(pk=profile_to_check.pk).exists()

    def is_followed_by(self, profile_to_check):
        """Проверяет, подписан ли другой профиль на текущий."""
        return self.followers.filter(pk=profile_to_check.pk).exists()


# --- МОДЕЛЬ EmailVerificationCode УДАЛЕНА ---
# (Код был здесь)
# --------------------------------------------

# --- Сигнал для профиля (немного улучшен) ---
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Создает профиль при создании пользователя или
    гарантирует его наличие при обновлении (на всякий случай).
    """
    if created:
        Profile.objects.create(user=instance)
        # print(f"Profile created for new user: {instance.username}") # Отладку можно убрать
    else:
        # При обновлении пользователя, просто убедимся, что профиль есть
        # Обычно сохранять его не нужно, если данные профиля не зависят от данных User
        Profile.objects.get_or_create(user=instance)
        # print(f"Checked/Ensured profile exists for updated user: {instance.username}")