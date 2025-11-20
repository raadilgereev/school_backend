from django.db import models
import os



class Teacher(models.Model):
    name = models.CharField(max_length=120)                 # ФИО учителя
    subject = models.CharField(max_length=120, blank=True)  # Предмет (может быть пустым)
    bio = models.TextField(blank=True)                      # Краткая биография
    email = models.EmailField(blank=True)                   # Email (опционально)
    phone = models.CharField(max_length=50, blank=True)     # Телефон (опционально)
    photo = models.ImageField(upload_to='teachers/', blank=True, null=True)  # Фото (сохраняется в media/teachers/)
    is_active = models.BooleanField(default=True)           # Активен ли (показывать на сайте)
    order = models.PositiveIntegerField(default=0)          # Порядок отображения (меньше число — выше в списке)

    class Meta:
        ordering = ['order', 'name']                        # Сортировка по order, затем по имени
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'

    def __str__(self):
        return self.name                                    # В админке будет отображаться имя
    

class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]          # Варианты рейтинга (1–5), чтобы нельзя было ввести другое число

    name = models.CharField(max_length=120, blank=True)     # Имя автора (может быть пустым → аноним)
    text = models.TextField()                               # Текст отзыва
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)  # Оценка от 1 до 5
    created_at = models.DateTimeField(auto_now_add=True)    # Дата и время создания отзыва

    ip_address = models.GenericIPAddressField(null=True, blank=True) # IP адрес пользователя (сохраняется автоматически)
    user_agent = models.TextField(blank=True)               # User-Agent браузера (для аналитики/антиспама)

    class Meta:
        ordering = ['-created_at']                          # Новые отзывы сверху
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        constraints = [
            models.CheckConstraint(                         # Проверка: рейтинг только в диапазоне 1–5
                check=models.Q(rating__gte=1, rating__lte=5),
                name='review_rating_between_1_and_5',
            ),
        ]

    def __str__(self):
        return f"{self.name or 'Аноним'} ({self.rating})"  # В админке будет видно автора и оценку
    

class SchoolInfo(models.Model):
    address = models.CharField(max_length=255, blank=True)  # Адрес школы
    email = models.EmailField(blank=True)                   # Общая почта
    phone = models.CharField(max_length=50, blank=True)     # Телефон
    about = models.TextField(blank=True)                    # Текст «О школе»
    map_iframe = models.TextField(blank=True)               # HTML iframe карты (Google/Яндекс)

    class Meta:
        verbose_name = 'Информация о школе'
        verbose_name_plural = 'Информация о школе'

    def __str__(self):
        return 'Информация о школе'                         # В админке будет фиксированное название
    



class Document(models.Model):
    AUDIENCE_CHOICES = [
        ('ALL', 'Все'),
        ('TEACHERS', 'Учителя'),
        ('PARENTS', 'Родители'),
        ('STUDENTS', 'Ученики'),
    ]

    title = models.CharField(max_length=200)                # Название документа
    category = models.CharField(max_length=120, blank=True) # Категория (например, «Учебные материалы»)
    description = models.TextField(blank=True)              # Краткое описание
    audience = models.CharField(                            # Для кого предназначен документ
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='ALL',
    )
    file = models.FileField(upload_to='docs/%Y/%m')         # Файл сохраняется в media/docs/год/месяц
    original_name = models.CharField(max_length=255, blank=True) # Оригинальное имя файла (для скачивания)
    is_public = models.BooleanField(default=True, db_index=True) # Флаг: показывать ли на сайте
    uploaded_at = models.DateTimeField(auto_now_add=True)   # Дата загрузки

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"  # В админке будет видно и название, и аудиторию

    def save(self, *args, **kwargs):
        if not self.original_name and self.file and hasattr(self.file, 'name'):
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)