from django.contrib import admin

# Register your models here.
from .models import SubscriptionPlan, UserSubscription

admin.site.register(SubscriptionPlan)
admin.site.register(UserSubscription)
