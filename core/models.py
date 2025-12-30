from __future__ import annotations

import os
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


# -------------------------
# School site models
# -------------------------

class Teacher(models.Model):
    name = models.CharField(max_length=120)
    subject = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to="teachers/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Преподаватель"
        verbose_name_plural = "Преподаватели"
        indexes = [
            models.Index(fields=["is_active", "order"], name="idx_teacher_active_order"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(order__gte=0), name="teacher_order_gte_0"),
        ]

    def __str__(self):
        return self.name


class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    name = models.CharField(max_length=120, blank=True)
    text = models.TextField()
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        indexes = [
            models.Index(fields=["created_at"], name="idx_review_created_at"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.name or 'Аноним'} ({self.rating})"


class SchoolInfo(models.Model):
    address = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    about = models.TextField(blank=True)
    map_iframe = models.TextField(blank=True)

    class Meta:
        verbose_name = "Информация о школе"
        verbose_name_plural = "Информация о школе"

    def __str__(self):
        return "Информация о школе"


class Document(models.Model):
    AUDIENCE_CHOICES = [
        ("ALL", "Все"),
        ("TEACHERS", "Учителя"),
        ("PARENTS", "Родители"),
        ("STUDENTS", "Ученики"),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default="ALL")
    file = models.FileField(upload_to="docs/%Y/%m")
    original_name = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        indexes = [
            models.Index(fields=["is_public", "uploaded_at"], name="idx_doc_public_uploaded"),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"

    def save(self, *args, **kwargs):
        if not self.original_name and self.file and hasattr(self.file, "name"):
            self.original_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)


# -------------------------
# Merch / Shop models (API v1)
# -------------------------

class MerchCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True, verbose_name=_("Название"))
    slug = models.SlugField(max_length=140, unique=True, blank=True, verbose_name=_("Slug"))

    class Meta:
        verbose_name = "Категория мерча"
        verbose_name_plural = "Категории мерча"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_merchcat_name"),
            models.Index(fields=["slug"], name="idx_merchcat_slug"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    ВАЖНО: публичный id для API v1 = uuid (строка UUID).
    PK оставляем обычным int, чтобы ничего не ломать в админке/старых данных.
    """
    name = models.CharField(max_length=200, verbose_name=_("Название"))
    description = models.TextField(blank=True, default="", verbose_name=_("Описание"))

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Цена"),
    )

    category = models.ForeignKey(
        MerchCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
        verbose_name=_("Категория"),
    )

    in_stock = models.BooleanField(default=True, verbose_name=_("В наличии"))

    # опциональные массивы: ["S","M","L"] / ["Black","Blue"]
    sizes = models.JSONField(null=True, blank=True, default=None, verbose_name=_("Размеры"))
    colors = models.JSONField(null=True, blank=True, default=None, verbose_name=_("Цвета"))

    # твои старые поля можно оставить (они не мешают API v1)
    size = models.CharField(max_length=120, blank=True, verbose_name=_("Размер (старое поле)"))
    comment = models.TextField(blank=True, verbose_name=_("Комментарий (старое поле)"))

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создано"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлено"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            models.Index(fields=["in_stock"], name="idx_product_in_stock"),
            models.Index(fields=["category"], name="idx_product_category"),
            models.Index(fields=["name"], name="idx_product_name"),
            models.Index(fields=["created_at"], name="idx_product_created_at"),
        ]

    def __str__(self) -> str:
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Товар"),
    )
    image = models.ImageField(upload_to="products/%Y/%m/", verbose_name=_("Фото"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Загружено"))

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товаров"
        constraints = [
            models.UniqueConstraint(fields=["product", "order"], name="uniq_product_image_order"),
            models.CheckConstraint(check=models.Q(order__gte=0), name="product_image_order_gte_0"),
        ]
        indexes = [
            models.Index(fields=["product", "order"], name="idx_product_order"),
        ]

    def __str__(self) -> str:
        filename = os.path.basename(self.image.name) if self.image else "image"
        return f"{self.product_id}: {filename}"


class Order(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    order_number = models.CharField(max_length=32, unique=True, blank=True)

    parent_name = models.CharField(max_length=200)
    children_names = models.CharField(max_length=500)
    phone = models.CharField(max_length=15)

    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    comment = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка (заказ мерча)"
        verbose_name_plural = "Заявки (заказы мерча)"
        indexes = [
            models.Index(fields=["created_at"], name="idx_order_created_at"),
            models.Index(fields=["phone"], name="idx_order_phone"),
            models.Index(fields=["order_number"], name="idx_order_number"),
        ]

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        if creating and not self.order_number:
            year = (self.created_at or timezone.now()).year
            self.order_number = f"ORD-{year}-{self.id:06d}"
            Order.objects.filter(pk=self.pk).update(order_number=self.order_number)

    def __str__(self):
        return self.order_number or str(self.uuid)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField()

    selected_size = models.CharField(max_length=50, null=True, blank=True)
    selected_color = models.CharField(max_length=50, null=True, blank=True)

    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    name_at_order = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        indexes = [
            models.Index(fields=["order"], name="idx_orderitem_order"),
            models.Index(fields=["product"], name="idx_orderitem_product"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=1), name="orderitem_qty_gte_1"),
        ]

    def __str__(self):
        return f"{self.order_id}: {self.name_at_order} x {self.quantity}"