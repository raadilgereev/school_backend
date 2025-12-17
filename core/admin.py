# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Teacher, Review, SchoolInfo, Document, Product, ProductImage
from django.utils.html import format_html
from .models import Product, ProductImage


# 8.1. Админ для учителей: список, поиск, фильтры, мини-превью фото
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        'order',                # порядок (для ручной сортировки)
        'name',                 # имя
        'subject',              # предмет
        'email',                # email
        'is_active',            # опубликован?
        'photo_thumb',          # миниатюра фото (только просмотр)
    )
    list_display_links = ('name',)
    list_editable = ('is_active', 'order',)           # можно править прямо в списке
    list_filter = ('is_active', 'subject',)           # фильтры справа
    search_fields = ('name', 'subject', 'email',)     # строка поиска сверху
    ordering = ('order', 'name')                      # дефолтная сортировка

    def photo_thumb(self, obj):
        # маленькая превьюшка в списке (если фото загружено)
        if obj.photo:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.photo.url)
        return '—'
    photo_thumb.short_description = 'Фото'


# 8.2. Админ для отзывов: база для контроля и быстрой модерации при необходимости
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'name', 'rating', 'short_text')  # ключевые поля в списке
    list_filter = ('rating',)                                      # фильтр по оценке
    search_fields = ('name', 'text', 'ip_address', 'user_agent')   # поиск по имени/тексту/тех. полям
    date_hierarchy = 'created_at'                                  # навигация по дате сверху

    def short_text(self, obj):
        # компактный текст для списка (первые ~80 символов)
        t = (obj.text or '').strip()
        return t if len(t) <= 80 else t[:77] + '…'
    short_text.short_description = 'Текст'


# 8.3. Админ для информации о школе: одна запись, без лишних столбцов
@admin.register(SchoolInfo)
class SchoolInfoAdmin(admin.ModelAdmin):
    list_display = ('address', 'email', 'phone')      # показываем кратко
    # TIP: обычно это «одиночка». Можно в админке создать ровно одну запись,
    # дальше править всегда её (pk=1). Во view мы уже делаем get_or_create(pk=1).


# 8.4. Админ для документов: публикация/скрытие, фильтры, быстрые действия
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'uploaded_at',          # когда загружен
        'title',                # название
        'category',             # категория
        'audience',             # для кого (ALL/TEACHERS/PARENTS/STUDENTS)
        'is_public',            # виден ли гостям
        'original_name',        # оригинальное имя файла
    )
    list_filter = ('is_public', 'category', 'audience')   # фильтры
    search_fields = ('title', 'description', 'original_name')  # поиск
    date_hierarchy = 'uploaded_at'                        # навигация по датам
    actions = ('make_public', 'make_private',)            # массовые действия
    readonly_fields = ()                                  # все можно править; оставим пустым

    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f'Опубликовано: {updated} документ(ов).')
    make_public.short_description = 'Сделать публичными'

    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f'Скрыто: {updated} документ(ов).')
    make_private.short_description = 'Сделать скрытыми'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ('order', 'image', 'image_thumb', 'uploaded_at')
    readonly_fields = ('image_thumb', 'uploaded_at')

    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.image.url)
        return '—'
    image_thumb.short_description = 'Превью'



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("order", "image", "image_thumb", "uploaded_at")
    readonly_fields = ("image_thumb", "uploaded_at")

    def image_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    image_thumb.short_description = "Превью"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "size", "created_at", "updated_at")
    search_fields = ("name", "comment", "size")
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "order", "image_thumb", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("product__name",)
    ordering = ("product", "order", "id")
    readonly_fields = ("image_thumb", "uploaded_at")

    def image_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    image_thumb.short_description = "Фото"