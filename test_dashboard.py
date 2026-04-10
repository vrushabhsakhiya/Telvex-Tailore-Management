import os
import django
import dj_database_url

os.environ["DATABASE_URL"] = "postgresql://taivexuser:30rbGXfTtcwlJb52yWxE7RFYawfFMU1C@dpg-d75o25muk2gs73dcqvig-a.oregon-postgres.render.com/taivex"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
request = RequestFactory().get('/dashboard/')

print(f"Total Users in Prod DB: {User.objects.count()}")

# Testing for all users just to be sure
for user in User.objects.all():
    request.user = user
    from store.views import dashboard
    try:
        response = dashboard(request)
        if hasattr(response, 'render'):
            response.render()
        print(f'SUCCESS for user {user.username}')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'ERROR for user {user.username}:', e)
