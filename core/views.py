# core/views.py
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Teacher, Review, SchoolInfo, Document
from .serializers import TeacherSerializer, ReviewSerializer, SchoolInfoSerializer, DocumentSerializer


class TeacherViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TeacherSerializer

    def get_queryset(self):
        qs = Teacher.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs.order_by("order", "name")

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reviews"

    def get_queryset(self):
        return Review.objects.all().order_by("-created_at")

    def get_permissions(self):
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save()


class SchoolInfoViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = SchoolInfo.objects.all()
    serializer_class = SchoolInfoSerializer

    def list(self, request, *args, **kwargs):
        obj, _ = SchoolInfo.objects.get_or_create(pk=1)
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class DocumentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.all()

        audience = self.request.query_params.get("audience")
        if audience:
            qs = qs.filter(audience=audience)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        if not self.request.user.is_staff:
            qs = qs.filter(is_public=True)

        return qs.order_by("-uploaded_at")

    def get_permissions(self):
        if self.request.method in ("POST", "DELETE"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=["get"], url_path="download", url_name="download")
    def download(self, request, pk=None):
        doc = get_object_or_404(self.get_queryset(), pk=pk)
        if not doc.file:
            raise Http404("Файл не найден")

        filename = doc.original_name or os.path.basename(doc.file.name)
        return FileResponse(doc.file.open("rb"), as_attachment=True, filename=filename)