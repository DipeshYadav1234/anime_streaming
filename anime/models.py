from django.db import models

# Create your models here.

from django.contrib.auth.models import User

class WatchList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mal_id = models.IntegerField()
    title = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "mal_id")

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    price = models.IntegerField()  # monthly price
    can_watch = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.plan.name}"