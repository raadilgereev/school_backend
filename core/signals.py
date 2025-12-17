# app/signals.py
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import ProductImage

@receiver(post_delete, sender=ProductImage)
def product_image_delete_file(sender, instance: ProductImage, **kwargs):
    # Удаляем файл после удаления записи
    if instance.image:
        instance.image.delete(save=False)

@receiver(pre_save, sender=ProductImage)
def product_image_replace_file(sender, instance: ProductImage, **kwargs):
    # Если файл у записи меняется — удалить старый
    if not instance.pk:
        return
    try:
        old = ProductImage.objects.get(pk=instance.pk)
    except ProductImage.DoesNotExist:
        return

    if old.image and old.image != instance.image:
        old.image.delete(save=False)