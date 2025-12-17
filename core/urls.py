# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TeacherViewSet,
    ReviewViewSet,
    SchoolInfoViewSet,
    DocumentViewSet,
    ProductViewSet,
    ProductImageViewSet,
)

router = DefaultRouter()
router.register(r'teachers', TeacherViewSet, basename='teacher')   # /api/teachers/
router.register(r'reviews', ReviewViewSet, basename='review')      # /api/reviews/
router.register(r'school', SchoolInfoViewSet, basename='school')   # /api/school/
router.register(r'documents', DocumentViewSet, basename='document')# /api/documents/
router.register(r'products', ProductViewSet, basename='product')   # /api/products/
router.register(r'product-images', ProductImageViewSet, basename='product-image')  # /api/product-images/

urlpatterns = [
    path('', include(router.urls)),
]
