from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('store.urls')),
    path('customers/', include('customers.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    from users.views import protected_media
    urlpatterns += [
        path('media/<path:path>', protected_media, name='protected_media'),
    ]
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # Disabled for security testing
