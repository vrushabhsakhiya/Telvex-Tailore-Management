from django.conf import settings

def shop_context(request):
    context = {
        'shop': None,
        'staff_name': None,
        'staff_role': None,
        'RECAPTCHA_PUBLIC_KEY': settings.RECAPTCHA_PUBLIC_KEY
    }
    
    if request.user.is_authenticated:
        try:
            shop = ShopProfile.objects.get(user=request.user)
            context['shop'] = shop
            context['staff_name'] = getattr(request, 'staff_name', None)
            context['staff_role'] = getattr(request, 'staff_role', None)
        except ShopProfile.DoesNotExist:
            pass
            
    return context
