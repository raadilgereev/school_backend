# core/views.py
from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from .models import Teacher, Review, SchoolInfo, Document
from .serializers import TeacherSerializer, ReviewSerializer, SchoolInfoSerializer, DocumentSerializer
import os

# 6.1. TeacherViewSet — CRUD для учителей (чтение всем, запись только админу)
class TeacherViewSet(mixins.ListModelMixin,            # GET /teachers/
                     mixins.RetrieveModelMixin,        # GET /teachers/{id}/
                     mixins.CreateModelMixin,          # POST /teachers/ (только админ)
                     mixins.UpdateModelMixin,          # PUT/PATCH /teachers/{id}/ (только админ)
                     mixins.DestroyModelMixin,         # DELETE /teachers/{id}/ (только админ)
                     viewsets.GenericViewSet):
    serializer_class = TeacherSerializer

    def get_queryset(self):
        # Гостям показываем только активных; админу — всех
        qs = Teacher.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs.order_by('order', 'name')

    def get_permissions(self):
        # Создание/обновление/удаление — только админ
        if self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


# 6.2. ReviewViewSet — список отзывов и создание (без модерации)
class ReviewViewSet(mixins.ListModelMixin,             # GET /reviews/
                    mixins.CreateModelMixin,           # POST /reviews/ (анонимно)
                    viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    throttle_classes = [ScopedRateThrottle]            # Троттлинг на создание отзывов
    throttle_scope = 'reviews'                         # См. DEFAULT_THROTTLE_RATES['reviews'] в settings.py

    def get_queryset(self):
        # Показываем все отзывы (модерации нет)
        return Review.objects.all().order_by('-created_at')

    def get_permissions(self):
        # Все могут читать и создавать отзыв
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        # Технические поля (ip/user_agent) проставляются в serializer.create(...)
        serializer.save()


# 6.3. SchoolInfoViewSet — одна запись с контактами/описанием
class SchoolInfoViewSet(mixins.ListModelMixin,         # GET /school/  → вернёт ровно 1 запись
                        mixins.UpdateModelMixin,       # PATCH/PUT /school/1  (только админ)
                        viewsets.GenericViewSet):
    queryset = SchoolInfo.objects.all()
    serializer_class = SchoolInfoSerializer

    def list(self, request, *args, **kwargs):
        # Если записи нет — создаём пустую, чтобы фронту всегда было что отдать
        obj, _ = SchoolInfo.objects.get_or_create(pk=1)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


# 6.4. DocumentViewSet — список/деталь/загрузка/удаление + скачивание
class DocumentViewSet(mixins.ListModelMixin,           # GET /documents/
                      mixins.RetrieveModelMixin,       # GET /documents/{id}/
                      mixins.CreateModelMixin,         # POST /documents/ (только админ)
                      mixins.DestroyModelMixin,        # DELETE /documents/{id}/ (только админ)
                      viewsets.GenericViewSet):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.all()

        # Фильтрация по аудитории/категории через query-параметры (опционально для фронта):
        # /api/documents/?audience=TEACHERS&category=Отчеты
        audience = self.request.query_params.get('audience')
        if audience:
            qs = qs.filter(audience=audience)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        # Негостевые документы скрываем от не-админов
        if not self.request.user.is_staff:
            qs = qs.filter(is_public=True)

        return qs.order_by('-uploaded_at')

    def get_permissions(self):
        if self.request.method in ('POST', 'DELETE'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=['get'], url_path='download', url_name='download')
    def download(self, request, pk=None):
        """
        GET /api/documents/{id}/download/
        """
        doc = get_object_or_404(self.get_queryset(), pk=pk)
        if not doc.file:
            raise Http404('Файл не найден')

        # Имя файла в Content-Disposition: берём original_name, если есть
        filename = doc.original_name or os.path.basename(doc.file.name)
        return FileResponse(doc.file.open('rb'), as_attachment=True, filename=filename)