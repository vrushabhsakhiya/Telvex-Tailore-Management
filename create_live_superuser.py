import os
import django

# Force connection to Live Render Database
os.environ["DATABASE_URL"] = "postgresql://taivexuser:30rbGXfTtcwlJb52yWxE7RFYawfFMU1C@dpg-d75o25muk2gs73dcqvig-a.oregon-postgres.render.com/taivex"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print("--- Live Database Superuser Creator ---")
email = input("Enter Email for new Superuser: ").strip()
username = input("Enter Username: ").strip()
password = input("Enter Password: ").strip()

if User.objects.filter(email=email).exists():
    print(f"\nError: A user with the email {email} already exists.")
else:
    User.objects.create_superuser(username, email, password)
    print(f"\nSuccess! Superuser '{email}' created on the Live Server!")
