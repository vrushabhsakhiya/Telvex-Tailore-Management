from .models import ShopProfile

def shop_context(request):
    if request.user.is_authenticated:
        try:
            shop = ShopProfile.objects.get(user=request.user)
            staff_name = getattr(request, 'staff_name', None)
            staff_role = getattr(request, 'staff_role', None)
            return {
                'shop': shop,
                'staff_name': staff_name,
                'staff_role': staff_role
            }
        except ShopProfile.DoesNotExist:
            return {'shop': None, 'staff_name': None, 'staff_role': None}
    return {'shop': None, 'staff_name': None, 'staff_role': None}
