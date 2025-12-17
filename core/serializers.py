# core/serializers.py
from rest_framework import serializers
from django.db import models
from django.urls import reverse
from .models import Teacher, Review, SchoolInfo, Document, Product, ProductImage

from django.db import transaction
from django.db.models import Max
from django.core.validators import FileExtensionValidator
from .models import Product, ProductImage

class TeacherSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField(read_only=True)  # Абсолютный URL на фото

    class Meta:
        model = Teacher
        fields = (
            'id', 'name', 'subject', 'bio',
            'email', 'phone', 'photo', 'photo_url'
        )
        read_only_fields = ('id', 'photo_url')  # id и photo_url — только на чтение

    def get_photo_url(self, obj):
        # Возвращаем абсолютную ссылку на фото (или None, если фото нет)
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url if obj.photo else None
    

class ReviewSerializer(serializers.ModelSerializer):
    # created_at только на чтение: ставится автоматически в модели
    class Meta:
        model = Review
        fields = ('id', 'name', 'text', 'rating', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_rating(self, value):
        # Доп. защита: рейтинг строго 1..5 (дублирует CheckConstraint в БД)
        if not (1 <= value <= 5):
            raise serializers.ValidationError('Рейтинг должен быть от 1 до 5')
        return value

    def validate_text(self, value):
        # Пример минимальной валидации содержания
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Текст отзыва слишком короткий')
        return value

    def create(self, validated_data):
        # IP и User-Agent не приходят от клиента — достанем из контекста запроса в View
        request = self.context.get('request')
        if request:
            validated_data.setdefault('ip_address', request.META.get('REMOTE_ADDR'))
            validated_data.setdefault('user_agent', request.META.get('HTTP_USER_AGENT', ''))
        return super().create(validated_data)
    

class SchoolInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolInfo
        fields = ('id', 'address', 'email', 'phone', 'about', 'map_iframe')
        read_only_fields = ('id',)  # id на чтение, остальное можно править админом через API/админку



class DocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField(read_only=True)  # Прямая ссылка на скачивание
    file_url = serializers.SerializerMethodField(read_only=True)      # Абсолютный URL на сам файл
    audience_label = serializers.SerializerMethodField(read_only=True) # Человекочитаемая аудитория

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'category', 'description',
            'audience', 'audience_label',
            'file', 'file_url', 'original_name',
            'is_public', 'uploaded_at',
            'download_url',
        )
        read_only_fields = ('id', 'uploaded_at', 'download_url', 'file_url', 'audience_label')

    def get_download_url(self, obj):
        # Строим URL на кастомный endpoint скачивания: /api/documents/{id}/download/
        request = self.context.get('request')
        url = reverse('document-download', args=[obj.pk])
        return request.build_absolute_uri(url) if request else url

    def get_file_url(self, obj):
        # Абсолютный URL хранения файла (MEDIA); это НЕ «скачать», а прямая ссылка на файл
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def get_audience_label(self, obj):
        # Возвращаем человекочитаемую подпись для audience (например, «Учителя»)
        return obj.get_audience_display()

    # Примеры валидаций «на вырост» (раскомментируй при необходимости):
    # def validate_file(self, value):
    #     # Ограничим размер файла, например, 10 МБ
    #     max_size = 10 * 1024 * 1024
    #     if value.size > max_size:
    #         raise serializers.ValidationError('Файл слишком большой (лимит 10 МБ)')
    #     # Ограничим типы: только pdf/docx/xlsx
    #     allowed_ext = ('.pdf', '.docx', '.xlsx')
    #     import os
    #     _, ext = os.path.splitext(value.name.lower())
    #     if ext not in allowed_ext:
    #         raise serializers.ValidationError('Разрешены только PDF, DOCX, XLSX')
    #     return value



MAX_IMAGES_PER_PRODUCT = 10
MAX_IMAGE_SIZE_MB = 8

def validate_image_size(file):
    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise serializers.ValidationError(
            f"Слишком большой файл (> {MAX_IMAGE_SIZE_MB} MB)."
        )

class ProductImageNestedSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image_url", "order", "uploaded_at")
        read_only_fields = fields

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Для отдельного эндпоинта /api/product-images/
    Тут product нужен.
    """
    image_url = serializers.SerializerMethodField(read_only=True)
    image = serializers.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ]
    )

    class Meta:
        model = ProductImage
        fields = ("id", "product", "image", "image_url", "order", "uploaded_at")
        read_only_fields = ("id", "image_url", "uploaded_at")

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageNestedSerializer(many=True, read_only=True)

    # 1) загрузка пачкой
    upload_images = serializers.ListField(
        child=serializers.ImageField(
            validators=[
                FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
                validate_image_size,
            ]
        ),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    # 3) режимы управления фото
    replace_images = serializers.BooleanField(write_only=True, required=False, default=False)
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    # Например: [12, 9, 10] => этим id проставим order = 0,1,2
    images_order = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "price",
            "size",
            "comment",
            "created_at",
            "updated_at",
            "images",
            "upload_images",
            "replace_images",
            "delete_image_ids",
            "images_order",
        )
        read_only_fields = ("id", "created_at", "updated_at", "images")

    def _validate_images_limit(self, product: Product, new_count: int, replace: bool):
        existing = product.images.count() if product.pk else 0
        total = new_count if replace else existing + new_count
        if total > MAX_IMAGES_PER_PRODUCT:
            raise serializers.ValidationError(
                f"Слишком много фото. Максимум {MAX_IMAGES_PER_PRODUCT}."
            )

    def _apply_delete(self, product: Product, ids: list[int]):
        if not ids:
            return
        # удаляем только фото этого товара
        ProductImage.objects.filter(product=product, id__in=ids).delete()

    def _apply_reorder(self, product: Product, ordered_ids: list[int]):
        if not ordered_ids:
            return

        # Проверим, что все id принадлежат этому товару
        existing_ids = set(product.images.values_list("id", flat=True))
        ordered_set = set(ordered_ids)

        # Можно сделать строгую проверку (если пришли чужие id — ошибка)
        if not ordered_set.issubset(existing_ids):
            raise serializers.ValidationError("images_order содержит чужие/несуществующие id.")

        # Проставим order последовательно
        for idx, img_id in enumerate(ordered_ids):
            ProductImage.objects.filter(product=product, id=img_id).update(order=idx)

        # Остальным (которые не перечислены) — в хвост, сохраняя относительный порядок
        tail = product.images.exclude(id__in=ordered_ids).order_by("order", "id")
        start = len(ordered_ids)
        for j, img in enumerate(tail, start=start):
            if img.order != j:
                ProductImage.objects.filter(pk=img.pk).update(order=j)

    def _append_images(self, product: Product, files: list):
        if not files:
            return
        next_order = (product.images.aggregate(m=Max("order")).get("m") or -1) + 1
        for i, file in enumerate(files):
            ProductImage.objects.create(product=product, image=file, order=next_order + i)

    def _replace_images(self, product: Product, files: list):
        # удаляем все старые, затем добавляем новые с order=0..n
        product.images.all().delete()
        for i, file in enumerate(files):
            ProductImage.objects.create(product=product, image=file, order=i)

    @transaction.atomic  # 2) атомарность
    def create(self, validated_data):
        upload_images = validated_data.pop("upload_images", [])
        replace_images = validated_data.pop("replace_images", False)  # для create неважно
        delete_ids = validated_data.pop("delete_image_ids", [])
        order_ids = validated_data.pop("images_order", [])

        product = super().create(validated_data)

        self._validate_images_limit(product, len(upload_images), replace=True)
        if upload_images:
            # для create логичнее трактовать как replace
            self._replace_images(product, upload_images)

        # delete/order для create обычно не нужно, но оставим безопасно:
        self._apply_delete(product, delete_ids)
        self._apply_reorder(product, order_ids)
        return product

    @transaction.atomic  # 2) атомарность
    def update(self, instance, validated_data):
        upload_images = validated_data.pop("upload_images", [])
        replace_images = validated_data.pop("replace_images", False)
        delete_ids = validated_data.pop("delete_image_ids", [])
        order_ids = validated_data.pop("images_order", [])

        product = super().update(instance, validated_data)

        # 6) лимит фото
        self._validate_images_limit(product, len(upload_images), replace=replace_images)

        # 3) удаление выбранных
        self._apply_delete(product, delete_ids)

        # 3) replace/append
        if upload_images:
            if replace_images:
                self._replace_images(product, upload_images)
            else:
                self._append_images(product, upload_images)

        # 3) reorder
        self._apply_reorder(product, order_ids)

        return product