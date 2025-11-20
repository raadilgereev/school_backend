# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, ReviewViewSet, SchoolInfoViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'teachers', TeacherViewSet, basename='teacher')   # /api/teachers/
router.register(r'reviews', ReviewViewSet, basename='review')      # /api/reviews/
router.register(r'school', SchoolInfoViewSet, basename='school')   # /api/school/
router.register(r'documents', DocumentViewSet, basename='document')# /api/documents/

urlpatterns = [
    path('', include(router.urls)),
]