# core/admin.py
from django.contrib import admin
from django.utils.html import format_html

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


# -------------------------
# Teachers
# -------------------------

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "name",
        "subject",
        "email",
        "is_active",
        "photo_thumb",
    )
    list_display_links = ("name",)
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "subject")
    search_fields = ("name", "subject", "email")
    ordering = ("order", "name")

    def photo_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;" />',
                obj.photo.url,
            )
        return "—"

    photo_thumb.short_description = "Фото"


# -------------------------
# Reviews
# -------------------------

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "rating", "short_text")
    list_filter = ("rating",)
    search_fields = ("name", "text", "ip_address", "user_agent")
    date_hierarchy = "created_at"

    def short_text(self, obj):
        t = (obj.text or "").strip()
        return t if len(t) <= 80 else t[:77] + "…"

    short_text.short_description = "Текст"


# -------------------------
# School info
# -------------------------

@admin.register(SchoolInfo)
class SchoolInfoAdmin(admin.ModelAdmin):
    list_display = ("address", "email", "phone")


# -------------------------
# Documents
# -------------------------

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "uploaded_at",
        "title",
        "category",
        "audience",
        "is_public",
        "original_name",
    )
    list_filter = ("is_public", "category", "audience")
    search_fields = ("title", "description", "original_name")
    date_hierarchy = "uploaded_at"
    actions = ("make_public", "make_private")

    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f"Опубликовано: {updated} документ(ов).")

    make_public.short_description = "Сделать публичными"

    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f"Скрыто: {updated} документ(ов).")

    make_private.short_description = "Сделать скрытыми"


# -------------------------
# Merch categories
# -------------------------

@admin.register(MerchCategory)
class MerchCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "id")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}  # удобно в админке


# -------------------------
# Products + images
# -------------------------

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("order", "image", "image_thumb", "uploaded_at")
    readonly_fields = ("image_thumb", "uploaded_at")
    ordering = ("order", "id")

    def image_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    image_thumb.short_description = "Превью"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "in_stock",
        "uuid",
        "created_at",
        "updated_at",
    )
    list_filter = ("in_stock", "category")
    search_fields = ("name", "description", "comment", "size")
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [ProductImageInline]

    fieldsets = (
        ("Основное", {"fields": ("name", "description", "category", "price", "in_stock")}),
        ("Варианты (API v1)", {"fields": ("sizes", "colors")}),
        ("Старые поля (если используешь)", {"fields": ("size", "comment")}),
        ("Служебное", {"fields": ("uuid", "created_at", "updated_at")}),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "order", "image_thumb", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("product__name",)
    ordering = ("product", "order", "id")
    readonly_fields = ("image_thumb", "uploaded_at")

    def image_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    image_thumb.short_description = "Фото"


# -------------------------
# Orders
# -------------------------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product",
        "name_at_order",
        "price_at_order",
        "quantity",
        "selected_size",
        "selected_color",
    )
    readonly_fields = ("name_at_order", "price_at_order")
    autocomplete_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "parent_name",
        "phone",
        "total",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("order_number", "parent_name", "children_names", "phone")
    readonly_fields = ("uuid", "order_number", "created_at")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "name_at_order", "quantity", "price_at_order", "selected_size", "selected_color")
    search_fields = ("order__order_number", "name_at_order")
    list_filter = ("selected_size", "selected_color")
    autocomplete_fields = ("order", "product")