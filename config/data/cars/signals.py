from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Car, Notification, Details
from ..finans.models import Logs


@receiver(post_save, sender=Car)
def car_oil_recycle_notification(sender, instance: Car, created, **kwargs):
    """
    Маслога алоқадор notification:
    - check_oil_recycle_notification() True bo‘lsa, print ham, Notification ham yaratiladi.
    """
    if instance.check_oil_recycle_notification():
        msg_print = (
            f"Уведомление: Автомобиль {instance.name} "
            f"приближается к следующему пробегу для замены масла."
        )
        msg_db = (
            f"Автомобиль с номером {instance.number} "
            f"приближается к следующему пробегу для замены масла."
        )

        print(msg_print)
        Notification.objects.create(message=msg_db)


@receiver(post_save, sender=Car)
def on_car_create(sender, instance: Car, created, **kwargs):
    """
    CASH bo‘lsa — Logs ga outcome yozamiz.
    """
    if created and instance.type_of_payment == "CASH":
        Logs.objects.create(
            action="OUTCOME",
            amount_uzs=instance.price_uzs,
            amount=instance.price,
            amount_type=instance.price_type,
            kind="BUY_CAR",
            comment=f"За покупку техники / {instance.name} и {instance.number} ",
        )


@receiver(post_save, sender=Details)
def on_details_create(sender, instance: Details, created, **kwargs):
    """
    Detal yaratilganda Logs ga yozamiz.
    """
    if created:
        if instance.car is not None:
            comment = (
                f"Детали для машины {instance.car.name}-"
                f"{instance.car.number} обновлены."
            )
        else:
            # bu yerda '' ishlatyapmiz, f-string ichida kolliziya bo‘lmaydi
            comment = (
                f"Деталь ID {instance.id_detail or ''} "
                f"создана без привязки к машине"
            )

        Logs.objects.create(
            action="OUTCOME",
            amount_uzs=instance.price_uzs,
            amount=instance.price,
            amount_type=instance.price_type,
            car=instance.car,
            kind="OTHER",
            comment=comment,
        )
