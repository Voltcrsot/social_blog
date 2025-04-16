# users/forms.py

from django import forms
from django.contrib.auth import get_user_model
# Импортируем стандартные формы Django для аутентификации и регистрации
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Profile # Импортируем Profile, он нам понадобится

User = get_user_model()

# --- ФОРМА ВХОДА ---
# Мы можем использовать стандартную AuthenticationForm, но для кастомизации
# (например, добавления классов CSS или изменения меток) удобнее создать свою.
class UserLoginForm(AuthenticationForm):
    """Кастомная форма входа."""
    username = forms.CharField(
        label="Имя пользователя или Email", # Меняем метку
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Введите логин или email',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        label="Пароль",
        strip=False, # Оставляем как есть для AuthenticationForm
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
            'placeholder': 'Введите пароль',
            'autocomplete': 'current-password'
        }),
    )
    # Поле 'remember me' убираем, стандартная AuthenticationForm его не имеет.
    # Если оно нужно, придется добавлять его вручную и обрабатывать в представлении.

    # Можно добавить __init__ для доп. настроек, если нужно, но для начала необязательно
    # def __init__(self, request=None, *args, **kwargs):
    #     super().__init__(request=request, *args, **kwargs)
    #     # self.fields['username'].widget.attrs.update({'class': 'my-custom-class'})


# --- ФОРМА РЕГИСТРАЦИИ ---
# Наследуемся от UserCreationForm, который содержит логику создания User и хеширования пароля
class UserRegistrationForm(UserCreationForm):
    """Кастомная форма регистрации."""
    # Добавляем поле email и делаем его обязательным
    email = forms.EmailField(
        label="Email адрес",
        required=True,
        widget=forms.EmailInput(attrs={
             'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
             'placeholder': 'your@email.com',
             'autocomplete': 'email'
        })
    )
    # Можно добавить другие поля, например, first_name, last_name, если нужно
    first_name = forms.CharField(
        label="Имя",
        required=False, # Делаем необязательным
         widget=forms.TextInput(attrs={
             'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
             'placeholder': 'Ваше имя (необязательно)',
             'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        label="Фамилия",
        required=False, # Делаем необязательным
         widget=forms.TextInput(attrs={
             'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
             'placeholder': 'Ваша фамилия (необязательно)',
             'autocomplete': 'family-name'
        })
    )

    class Meta(UserCreationForm.Meta):
        # Берем за основу мета-класс родителя
        model = User
        # Указываем поля, которые будут в форме (включая email)
        fields = ('username', 'email', 'first_name', 'last_name') # 'password' добавляется UserCreationForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем классы к полям, унаследованным от UserCreationForm
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({
                 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                 'placeholder': 'Придумайте имя пользователя',
                 'autocomplete': 'username'
            })
        if 'password1' in self.fields: # UserCreationForm использует password1 и password2
            self.fields['password1'].label = "Придумайте пароль"
            self.fields['password1'].widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': '••••••••',
                'autocomplete': 'new-password'
            })
        if 'password2' in self.fields:
            self.fields['password2'].label = "Повторите пароль"
            self.fields['password2'].widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                'placeholder': '••••••••',
                'autocomplete': 'new-password'
            })

    def clean_email(self):
        """Проверка уникальности email."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Этот email адрес уже используется.")
        return email

    def save(self, commit=True):
        """Сохраняем пользователя и дополнительные поля."""
        user = super().save(commit=False) # Создаем пользователя, но не сохраняем
        # Сохраняем email и другие поля
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save() # Сохраняем пользователя в БД
            # Сигнал post_save должен автоматически создать Profile
        return user


# --- ФОРМА РЕДАКТИРОВАНИЯ USER (остается без изменений) ---
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email", required=True,
        widget=forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm', 'placeholder': 'your@email.com', 'autocomplete': 'email'})
    )
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm', 'placeholder': 'Имя', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm', 'placeholder': 'Фамилия', 'autocomplete': 'family-name'}),
        }

# --- ФОРМА РЕДАКТИРОВАНИЯ PROFILE (остается без изменений) ---
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm', 'placeholder': 'Расскажите немного о себе...'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer'}),
        }
        labels = {'bio': 'О себе', 'avatar': 'Аватар'}
        help_texts = {'avatar': 'Загрузите файл изображения (JPG, PNG, GIF). Текущий аватар будет заменен.'}