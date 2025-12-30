# core/serializers.py
from __future__ import annotations

import re
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.urls import reverse

from rest_framework import serializers
from django.core.validators import FileExtensionValidator

from .exceptions import ApiError

from .models import (
    Teacher,
    Review,
    SchoolInfo,
    Document,
    MerchCategory,
    Product,
    ProductImage,
    Order,
    OrderItem,
)

# =========================
# School serializers
# =========================

class TeacherSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Teacher
        fields = ("id", "name", "subject", "bio", "email", "phone", "photo", "photo_url")
        read_only_fields = ("id", "photo_url")

    def get_photo_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url if obj.photo else None


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("id", "name", "text", "rating", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
        return value

    def validate_text(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Текст отзыва слишком короткий")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            validated_data.setdefault("ip_address", request.META.get("REMOTE_ADDR"))
            validated_data.setdefault("user_agent", request.META.get("HTTP_USER_AGENT", ""))
        return super().create(validated_data)


class SchoolInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolInfo
        fields = ("id", "address", "email", "phone", "about", "map_iframe")
        read_only_fields = ("id",)


class DocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField(read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    audience_label = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "category",
            "description",
            "audience",
            "audience_label",
            "file",
            "file_url",
            "original_name",
            "is_public",
            "uploaded_at",
            "download_url",
        )
        read_only_fields = ("id", "uploaded_at", "download_url", "file_url", "audience_label")

    def get_download_url(self, obj) -> str:
        request = self.context.get("request")
        url = reverse("document-download", args=[obj.pk])
        return request.build_absolute_uri(url) if request else url

    def get_file_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def get_audience_label(self, obj) -> str:
        return obj.get_audience_display()


# =========================
# Admin CRUD (existing) - Products & images
# =========================

MAX_IMAGES_PER_PRODUCT = 10
MAX_IMAGE_SIZE_MB = 5  # было 8, по ТЗ 5MB

def validate_image_size(file):
    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise serializers.ValidationError(f"Слишком большой файл (> {MAX_IMAGE_SIZE_MB} MB).")


class ProductImageNestedSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "image_url", "order", "uploaded_at")
        read_only_fields = fields

    def get_image_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductImageSerializer(serializers.ModelSerializer):
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

    def get_image_url(self, obj) -> str | None:
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageNestedSerializer(many=True, read_only=True)

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

    replace_images = serializers.BooleanField(write_only=True, required=False, default=False)
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
        allow_empty=True,
    )
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
            "uuid",          # полезно видеть uuid в админском API
            "name",
            "description",   # добавили
            "category",      # добавили
            "in_stock",      # добавили
            "sizes",         # добавили
            "colors",        # добавили
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
        read_only_fields = ("id", "uuid", "created_at", "updated_at", "images")

    def _validate_images_limit(self, product: Product, new_count: int, replace: bool):
        existing = product.images.count() if product.pk else 0
        total = new_count if replace else existing + new_count
        if total > MAX_IMAGES_PER_PRODUCT:
            raise serializers.ValidationError(f"Слишком много фото. Максимум {MAX_IMAGES_PER_PRODUCT}.")

    def _apply_delete(self, product: Product, ids: list[int]):
        if not ids:
            return
        ProductImage.objects.filter(product=product, id__in=ids).delete()

    def _apply_reorder(self, product: Product, ordered_ids: list[int]):
        if not ordered_ids:
            return

        existing_ids = set(product.images.values_list("id", flat=True))
        ordered_set = set(ordered_ids)
        if not ordered_set.issubset(existing_ids):
            raise serializers.ValidationError("images_order содержит чужие/несуществующие id.")

        for idx, img_id in enumerate(ordered_ids):
            ProductImage.objects.filter(product=product, id=img_id).update(order=idx)

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
        product.images.all().delete()
        for i, file in enumerate(files):
            ProductImage.objects.create(product=product, image=file, order=i)

    @transaction.atomic
    def create(self, validated_data):
        upload_images = validated_data.pop("upload_images", [])
        _ = validated_data.pop("replace_images", False)
        delete_ids = validated_data.pop("delete_image_ids", [])
        order_ids = validated_data.pop("images_order", [])

        product = super().create(validated_data)

        self._validate_images_limit(product, len(upload_images), replace=True)
        if upload_images:
            self._replace_images(product, upload_images)

        self._apply_delete(product, delete_ids)
        self._apply_reorder(product, order_ids)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        upload_images = validated_data.pop("upload_images", [])
        replace_images = validated_data.pop("replace_images", False)
        delete_ids = validated_data.pop("delete_image_ids", [])
        order_ids = validated_data.pop("images_order", [])

        product = super().update(instance, validated_data)

        self._validate_images_limit(product, len(upload_images), replace=replace_images)
        self._apply_delete(product, delete_ids)

        if upload_images:
            if replace_images:
                self._replace_images(product, upload_images)
            else:
                self._append_images(product, upload_images)

        self._apply_reorder(product, order_ids)
        return product


# =========================
# API v1 (public) - Merch & Orders
# =========================

class MerchItemSerializer(serializers.ModelSerializer):
    # id в API v1 должен быть UUID строкой -> берём из Product.uuid
    id = serializers.UUIDField(source="uuid", read_only=True)

    image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    category = serializers.SerializerMethodField()
    inStock = serializers.BooleanField(source="in_stock")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "price",
            "image",
            "images",
            "category",
            "inStock",
            "sizes",
            "colors",
            "createdAt",
            "updatedAt",
        )

    def _abs(self, url: str | None):
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and url else url

    def get_image(self, obj) -> str | None:
        first = obj.images.order_by("order", "id").first()
        return self._abs(first.image.url) if first and first.image else None

    def get_images(self, obj) -> list[str]:
        return [self._abs(i.image.url) for i in obj.images.order_by("order", "id") if i.image]

    def get_category(self, obj) -> str | None:
        return obj.category.name if obj.category_id else None


class MerchCategorySerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MerchCategory
        fields = ("id", "name", "slug", "count")


class OrderItemInSerializer(serializers.Serializer):
    itemId = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)
    selectedSize = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    selectedColor = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CreateOrderSerializer(serializers.Serializer):
    parentName = serializers.CharField(min_length=2, max_length=200)
    childrenNames = serializers.CharField(min_length=2, max_length=500)
    phone = serializers.CharField()
    items = OrderItemInSerializer(many=True, allow_empty=False)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)
    comment = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_phone(self, v: str):
        digits = re.sub(r"\D+", "", v or "")
        if not (10 <= len(digits) <= 11):
            raise serializers.ValidationError("Телефон должен содержать 10-11 цифр.")
        return digits

    @transaction.atomic
    def create(self, validated):
        # 1) поднимем товары по uuid
        items_in = validated["items"]
        ids = [i["itemId"] for i in items_in]

        products = (
            Product.objects
            .select_related("category")
            .prefetch_related("images")
            .filter(uuid__in=ids)
        )
        by_uuid = {p.uuid: p for p in products}

        # 2) валидации + расчет суммы
        calc_total = Decimal("0.00")
        prepared: list[tuple[Product, int, str | None, str | None]] = []

        for idx, it in enumerate(items_in):
            p = by_uuid.get(it["itemId"])
            if not p:
                raise ApiError(
                    code="ITEM_NOT_FOUND",
                    message="Товар не найден",
                    status_code=404,
                    details={"field": f"items[{idx}].itemId", "message": "Товар не найден"},
                )

            if not p.in_stock:
                raise ApiError(
                    code="ITEM_OUT_OF_STOCK",
                    message="Товар отсутствует в наличии",
                    status_code=400,
                    details={"field": f"items[{idx}].itemId", "message": "Товар отсутствует в наличии"},
                )

            qty = it["quantity"]
            if not (1 <= qty <= 99):
                raise ApiError(
                    code="INVALID_QUANTITY",
                    message="Неверное количество",
                    status_code=400,
                    details={"field": f"items[{idx}].quantity", "message": "Неверное количество"},
                )

            sel_size = (it.get("selectedSize") or None)
            sel_color = (it.get("selectedColor") or None)

            # sizes/colors: если в продукте указаны варианты — выбранное значение обязательно
            if p.sizes:
                if not sel_size or sel_size not in p.sizes:
                    raise ApiError(
                        code="INVALID_SIZE",
                        message="Неверный размер товара",
                        status_code=400,
                        details={"field": f"items[{idx}].selectedSize", "message": "Неверный размер товара"},
                    )

            if p.colors:
                if not sel_color or sel_color not in p.colors:
                    raise ApiError(
                        code="INVALID_COLOR",
                        message="Неверный цвет товара",
                        status_code=400,
                        details={"field": f"items[{idx}].selectedColor", "message": "Неверный цвет товара"},
                    )

            calc_total += (p.price * qty)
            prepared.append((p, qty, sel_size, sel_color))

        # 3) total mismatch
        if calc_total != validated["total"]:
            raise ApiError(
                code="TOTAL_MISMATCH",
                message="Несоответствие общей суммы",
                status_code=400,
                details={"field": "total", "message": "Несоответствие общей суммы"},
            )

        # 4) создать заказ
        order = Order.objects.create(
            parent_name=validated["parentName"],
            children_names=validated["childrenNames"],
            phone=validated["phone"],
            total=validated["total"],
            comment=(validated.get("comment") or None),
        )

        # 5) позиции заказа со snapshot-данными
        for p, qty, sel_size, sel_color in prepared:
            OrderItem.objects.create(
                order=order,
                product=p,
                quantity=qty,
                selected_size=sel_size,
                selected_color=sel_color,
                price_at_order=p.price,
                name_at_order=p.name,
            )

        return order

class OrderCreatedOutSerializer(serializers.Serializer):
    orderId = serializers.UUIDField(source="uuid")
    orderNumber = serializers.CharField(source="order_number")
    message = serializers.CharField()