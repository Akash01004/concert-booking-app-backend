from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)

class Concert(models.Model):
    name = models.CharField(max_length=255)
    date_time = models.DateTimeField()
    venue = models.CharField(max_length=255)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    available_tickets = models.IntegerField(default=0)
    image = models.ImageField(upload_to='concert_images/', blank=True, null=True)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE, null=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    noofseat = models.IntegerField(default=1, null=True)
    quantity = models.PositiveIntegerField(default=1, null=True)
    total_price = models.FloatField(null=True)
