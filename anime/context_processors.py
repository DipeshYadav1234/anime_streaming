from .models import UserSubscription

def user_subscription(request):
    if request.user.is_authenticated:
        try:
            return {
                "user_subscription": UserSubscription.objects.get(user=request.user)
            }
        except UserSubscription.DoesNotExist:
            return {"user_subscription": None}
    return {"user_subscription": None}
