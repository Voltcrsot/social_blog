# posts/forms.py

from django import forms
from django.utils import timezone # Нужен для проверки времени
from .models import Post, Category, Comment

# --- Форма комментария (остается без изменений из вашего файла) ---
class CommentForm(forms.ModelForm):
    """Форма для добавления/редактирования комментариев."""
    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Напишите ваш комментарий...',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm',
                 'aria-label': 'Текст комментария', # Для доступности
            }),
        }
        labels = {
             'content': '', # Скрываем метку, т.к. есть placeholder
        }

# --- Обновленная форма поста с видимостью и расписанием ---
class PostForm(forms.ModelForm):
    """Форма для создания и редактирования постов."""
    # Поле для выбора категории (из вашего файла)
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False, # Категория не обязательна
        empty_label="-- Выберите категорию --",
        label="Категория",
        widget=forms.Select(attrs={
             'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm'
        })
    )

    # Поле для выбора видимости (используем RadioSelect)
    visibility = forms.ChoiceField(
        choices=Post.VISIBILITY_CHOICES,
        initial=Post.VISIBILITY_PUBLIC, # Значение по умолчанию
        widget=forms.RadioSelect, # Отображаем как радиокнопки
        label="Видимость поста",
        help_text="Выберите, кто сможет видеть ваш пост после публикации."
    )

    # Поле для запланированной публикации
    scheduled_at = forms.DateTimeField(
        label="Запланировать публикацию на",
        required=False, # Не обязательно, если публикуем сейчас
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local', # Нативный HTML5 виджет
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm',
            }),
        help_text="Оставьте пустым, чтобы опубликовать сразу (если выбрана видимость 'Всем' или 'Подписчикам')."
    )

    class Meta:
        model = Post
        # Поля, которые будут в форме
        fields = ['title', 'content', 'category', 'visibility'] # is_published и published_at управляются логикой формы
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': 'Введите заголовок поста'
            }),
            'content': forms.Textarea(attrs={
                'rows': 10,
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm',
                'placeholder': 'Напишите текст вашего поста...'
            }),
            # 'is_published' убрано из fields, управляется через visibility/scheduled_at
        }
        help_texts = {
            'title': 'Максимум 200 символов.',
             'category': 'Выберите категорию, к которой относится ваш пост (необязательно).',
        }
        labels = {
            'title': 'Заголовок',
            'content': 'Текст поста',
            # Метки для category и visibility заданы при определении полей выше
        }

    def clean_scheduled_at(self):
        """Проверка, что дата расписания не в прошлом."""
        scheduled_at = self.cleaned_data.get('scheduled_at')
        # Проверяем только если дата была указана
        if scheduled_at and scheduled_at < timezone.now():
            # Позволим небольшую погрешность в пару секунд на случай задержки отправки формы
            if (timezone.now() - scheduled_at).total_seconds() > 5:
                 raise forms.ValidationError("Дата публикации по расписанию не может быть в прошлом.")
        return scheduled_at

    def save(self, commit=True):
        """Переопределяем сохранение для установки is_published и published_at."""
        instance = super().save(commit=False) # Получаем объект поста, но пока не сохраняем в БД

        scheduled_at = self.cleaned_data.get('scheduled_at')
        visibility = self.cleaned_data.get('visibility')

        # Определяем статус и время публикации
        if visibility != Post.VISIBILITY_PRIVATE:
            # Если пост не приватный, он считается "готовым к публикации"
            instance.is_published = True
            if scheduled_at:
                # Если указана дата расписания, используем ее
                instance.published_at = scheduled_at
            else:
                # Если дата не указана, публикуем сейчас.
                # Но! Если пост уже существует и имеет дату публикации, не меняем ее.
                if not instance.pk or not instance.published_at:
                    instance.published_at = timezone.now()
        else:
            # Если видимость "Только мне", пост НЕ публикуется
            instance.is_published = False
            instance.published_at = None # Сбрасываем дату

        if commit:
            instance.save()
            # self.save_m2m() # Если бы были ManyToMany поля в fields

        return instance