# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TeacherViewSet,
    ReviewViewSet,
    SchoolInfoViewSet,
    DocumentViewSet,
)
from .views_shop_admin import (ProductViewSet, ProductImageViewSet)
# v1 endpoints по ТЗ подключим следующим шагом:
from .views_api_v1 import (
    MerchListAPIView,
    MerchDetailAPIView,
    MerchCategoriesAPIView,
    OrdersCreateAPIView,
)

router = DefaultRouter()
router.register(r"teachers", TeacherViewSet, basename="teacher")          # /api/teachers/
router.register(r"reviews", ReviewViewSet, basename="review")            # /api/reviews/
router.register(r"school", SchoolInfoViewSet, basename="school")         # /api/school/
router.register(r"documents", DocumentViewSet, basename="document")      # /api/documents/
router.register(r"products", ProductViewSet, basename="product")         # /api/products/
router.register(r"product-images", ProductImageViewSet, basename="product-image")  # /api/product-images/

urlpatterns = [
    # старые DRF роуты
    path("", include(router.urls)),

    # --- API v1 (ТЗ) ---
    path("v1/merch", MerchListAPIView.as_view()),
    path("v1/merch/<uuid:id>", MerchDetailAPIView.as_view()),
    path("v1/merch/categories", MerchCategoriesAPIView.as_view()),
    path("v1/orders", OrdersCreateAPIView.as_view()),
]