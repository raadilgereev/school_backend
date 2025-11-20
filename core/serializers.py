# core/serializers.py
from rest_framework import serializers
from django.urls import reverse
from .models import Teacher, Review, SchoolInfo, Document

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