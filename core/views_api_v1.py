# core/views_api_v1.py
from __future__ import annotations

import logging
import math

from django.db.models import Q, Count
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from rest_framework.generics import GenericAPIView

from .exceptions import ApiError
from .models import Product, MerchCategory
from .serializers import (
    MerchItemSerializer,
    MerchCategorySerializer,
    CreateOrderSerializer,
)

logger = logging.getLogger("core.orders")


def ok(data, http_status=200, cache_seconds: int | None = None):
    resp = Response({"success": True, "data": data}, status=http_status)
    if cache_seconds is not None:
        resp["Cache-Control"] = f"public, max-age={int(cache_seconds)}"
    return resp


def parse_bool(v: str | None):
    if v is None:
        return None
    v = str(v).strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


def parse_int(v, default: int, min_v: int, max_v: int):
    try:
        x = int(v)
    except Exception:
        return default
    return max(min_v, min(max_v, x))


class MerchListAPIView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "v1_merch"
    serializer_class = MerchItemSerializer

    def get(self, request):
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        page = parse_int(request.query_params.get("page"), default=1, min_v=1, max_v=10_000)
        limit = parse_int(request.query_params.get("limit"), default=20, min_v=1, max_v=100)

        in_stock = parse_bool(request.query_params.get("inStock"))
        if request.query_params.get("inStock") is not None and in_stock is None:
            raise ApiError(
                code="VALIDATION_ERROR",
                message="Ошибка валидации данных",
                status_code=400,
                details={"field": "inStock", "message": "Ожидается boolean (true/false)"},
            )

        qs = (
            Product.objects.all()
            .select_related("category")
            .prefetch_related("images")
        )

        if category:
            qs = qs.filter(category__name=category)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        if in_stock is not None:
            qs = qs.filter(in_stock=in_stock)

        qs = qs.order_by("-created_at")

        total = qs.count()
        total_pages = max(1, math.ceil(total / limit))
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * limit
        items = qs[offset : offset + limit]

        serializer = MerchItemSerializer(items, many=True, context={"request": request})

        categories = list(
            Product.objects.exclude(category__isnull=True)
            .values_list("category__name", flat=True)
            .distinct()
            .order_by("category__name")
        )

        data = {
            "items": serializer.data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
            },
            "categories": categories,
        }
        return ok(data, cache_seconds=60)


class MerchDetailAPIView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "v1_merch"
    serializer_class = MerchItemSerializer

    def get(self, request, id):
        product = (
            Product.objects.select_related("category")
            .prefetch_related("images")
            .filter(uuid=id)
            .first()
        )
        if not product:
            raise ApiError(code="NOT_FOUND", message="Ресурс не найден", status_code=404)

        serializer = MerchItemSerializer(product, context={"request": request})
        return ok(serializer.data, cache_seconds=60)


class MerchCategoriesAPIView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "v1_merch"
    serializer_class = MerchCategorySerializer

    def get(self, request):
        qs = (
            MerchCategory.objects.annotate(count=Count("products"))
            .order_by("name")
        )
        serializer = MerchCategorySerializer(qs, many=True)
        return ok(serializer.data, cache_seconds=300)


class OrdersCreateAPIView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "v1_orders"
    serializer_class = CreateOrderSerializer

    def post(self, request):
        s = CreateOrderSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        order = s.save()

        logger.info(
            "New order: %s phone=%s total=%s items=%s",
            order.order_number,
            order.phone,
            str(order.total),
            order.items.count(),
        )

        return ok(
            {
                "orderId": str(order.uuid),
                "orderNumber": order.order_number,
                "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.",
            },
            http_status=status.HTTP_201_CREATED,
            cache_seconds=None,
        )