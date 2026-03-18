from django.db import models
from django.conf import settings
from django.utils import timezone

class Customer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customers', null=True, db_constraint=False)
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=20)
    alt_mobile = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    whatsapp = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, blank=True, null=True)
    photo = models.CharField(max_length=200, blank=True, null=True) # Path string
    notes = models.TextField(blank=True, null=True)
    style_pref = models.CharField(max_length=200, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    created_date = models.DateTimeField(default=timezone.now)
    last_visit = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [['user', 'mobile']]

    def __str__(self):
        return f"{self.name} ({self.mobile})"

    @property
    def total_pending(self):
        # We will implement this once Order model is ready and linked
        # logic: sum(o.balance for o in self.orders.all())
        total = 0
        if hasattr(self, 'orders'):
            for o in self.orders.all():
                total += o.balance
        return total
