import os
import shutil
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Backs up the database (SQLite or Postgres) to the media/backups directory'

    def handle(self, *args, **options):
        # 1. Setup Backup Directory
        backup_root = settings.MEDIA_ROOT / 'backups' / 'database'
        os.makedirs(backup_root, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # 2. Identify Database Engine
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']
        name = db_settings['NAME']
        
        self.stdout.write(f"Starting backup for {engine}...")

        try:
            if 'sqlite3' in engine:
                # SQLite Backup (Copy File)
                source = name
                dest = backup_root / f"db_backup_{timestamp}.sqlite3"
                shutil.copy2(source, dest)
                self.stdout.write(self.style.SUCCESS(f"SQLite backup created at: {dest}"))

            elif 'postgresql' in engine:
                # Postgres Backup (pg_dump)
                # Ensure PGPASSWORD is set if password provided
                env = os.environ.copy()
                if db_settings.get('PASSWORD'):
                    env['PGPASSWORD'] = db_settings['PASSWORD']
                
                user = db_settings.get('USER', 'postgres')
                host = db_settings.get('HOST', 'localhost')
                port = db_settings.get('PORT', '5432')
                db_name = db_settings.get('NAME')

                dest = backup_root / f"pg_backup_{timestamp}.sql"
                
                # Construct command: pg_dump -U user -h host -p port dbname > dest
                # Note: We use shell=True for redirection, or safer subprocess with open file
                command = f"pg_dump -U {user} -h {host} -p {port} {db_name} > \"{dest}\""
                
                # Check if pg_dump is available
                if shutil.which('pg_dump') is None:
                    self.stdout.write(self.style.WARNING("pg_dump not found in PATH. Skipping Postgres backup."))
                else:
                    os.system(command) # Using os.system for simple redirection support
                    self.stdout.write(self.style.SUCCESS(f"Postgres backup created at: {dest}"))

            else:
                self.stdout.write(self.style.ERROR(f"Backup not implemented for engine: {engine}"))

            # 3. Cleanup Old Backups (Optional: Keep last 30)
            # ...

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Backup failed: {str(e)}"))
