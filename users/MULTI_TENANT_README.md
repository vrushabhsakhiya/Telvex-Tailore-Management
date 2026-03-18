# Multi-Tenant Database Architecture

This project now supports a multi-tenant database architecture where each shop gets its own isolated database while sharing a common main database for user management.

## Architecture Overview

### Main Database (`talvex_main`)
- **Users**: `users.User` - Authentication and user management
- **Shop Profiles**: `users.ShopProfile` - Shop registration and metadata
- **Global Data**: Django admin, sessions, permissions
- **Purpose**: Centralized user management and shop registration

### Shop Databases (`talvex_shop_{shop_id}`)
- **Customers**: Shop-specific customer data
- **Products/Inventory**: Shop-specific products and stock
- **Bills/Transactions**: Shop-specific billing data
- **Purpose**: Complete data isolation per shop

## Database Routing

The system automatically routes queries to the appropriate database:

- **User/Auth models** → Main database
- **Shop-specific models** (customers, store) → Shop's database
- **Context switching** via middleware based on logged-in user

### Automatic Database Registration at Startup

When the Django application starts, the system automatically:

1. **Discovers** all existing shop databases from the ShopProfile table
2. **Validates** each database configuration
3. **Registers** valid databases in Django's DATABASES setting
4. **Tests** connections to ensure databases are accessible
5. **Logs** results (success/failure counts)

This ensures all shop databases are available before the first request is processed, preventing "ConnectionDoesNotExist" errors.

**Key Features:**
- **Error Isolation**: One failed shop database doesn't prevent others from registering
- **Graceful Degradation**: Application starts even if some shops fail to register
- **Skip During Migrations**: Registration is skipped during `migrate` and `makemigrations` commands
- **Comprehensive Logging**: All registration attempts are logged with appropriate levels

## Setup Instructions

### 1. Initial Setup

```bash
# Run the setup script
python setup_databases.py
```

This creates the main database and runs initial migrations.

### 2. Create Superuser

```bash
python manage.py createsuperuser --database=main
```

### 3. Register Shops

When you create a new `ShopProfile`, the system automatically:
1. Creates a new database: `talvex_shop_{shop_id}`
2. Runs migrations for shop-specific apps
3. Updates the shop profile with the database name

## Usage Examples

### Creating a Shop (Automatic Database Creation)

```python
from users.models import User, ShopProfile

# Create a user
user = User.objects.create_user(
    username='shopowner',
    email='owner@shop.com',
    password='password'
)

# Create shop profile (this automatically creates the database)
shop = ShopProfile.objects.create(
    user=user,
    shop_name='My Shop',
    mobile='1234567890'
)

# The shop now has its own database: talvex_shop_1
print(f"Shop database: {shop.database_name}")
```

### Working with Shop Data

```python
from customers.models import Customer
from config.thread_local import shop_db_context

# The middleware automatically sets the database context
# when a shop user is logged in

# Manual context switching (if needed)
with shop_db_context('talvex_shop_1'):
    customers = Customer.objects.all()  # Queries shop_1 database
```

## Database Management

### Adding New Shop-Specific Models

1. Add the model to the appropriate app (`customers`, `store`, etc.)
2. The router will automatically direct it to shop databases
3. New shops will get the model via automatic migrations

### Manual Database Operations

```python
from users.database_manager import ShopDatabaseManager

# Create a shop database manually
db_name = ShopDatabaseManager.create_shop_database(shop_id, shop_name)

# Drop a shop database
ShopDatabaseManager.drop_shop_database(shop_id)

# Check if database exists
exists = ShopDatabaseManager.shop_database_exists(shop_id)
```

## File Structure

```
config/
├── db_router.py          # Database routing logic
├── thread_local.py       # Thread-local storage for context
└── settings.py           # Database configuration

users/
├── models.py                  # User and ShopProfile models
├── database_manager.py        # Database creation/management
├── database_registration.py   # Startup database registration
├── signals.py                 # Auto database creation on shop registration
├── middleware.py              # Context switching middleware
└── apps.py                    # App configuration and startup hooks

setup_databases.py        # Initial setup script
```

## Security Benefits

1. **Data Isolation**: Each shop's data is completely isolated
2. **Scalability**: Can distribute databases across servers
3. **Backup Granularity**: Backup/restore individual shops
4. **Performance**: No cross-shop query interference
5. **Compliance**: Easier to meet data residency requirements

## Migration Strategy

### For Existing Single-Database Setup

1. **Backup**: Create a full backup of your existing database
2. **Setup**: Run `python setup_databases.py`
3. **Migrate Users**: Users and ShopProfiles move to main database
4. **Split Data**: Shop-specific data moves to individual databases
5. **Update**: Deploy the new code with database routing

### Database Names

- **Main**: `talvex_main`
- **Shops**: `talvex_shop_{shop_id}` (e.g., `talvex_shop_1`, `talvex_shop_42`)

## Troubleshooting

### Common Issues

1. **Database Creation Fails**: Check PostgreSQL permissions
2. **Migration Errors**: Ensure database exists and has correct permissions
3. **Context Not Set**: Verify middleware is properly configured
4. **ConnectionDoesNotExist Error**: Shop database not registered at startup
   - Check application logs for registration errors
   - Verify ShopProfile has database_name field set
   - Ensure database exists in PostgreSQL
   - Check database connection parameters

### Error Scenarios and Recovery

#### Shop Database Registration Fails at Startup

**Symptoms**: Application starts but specific shop gets "ConnectionDoesNotExist" error

**Causes**:
- Database doesn't exist in PostgreSQL
- Invalid connection parameters
- Network/connectivity issues
- PostgreSQL permissions

**Recovery**:
1. Check application logs for specific error message
2. Verify database exists: `psql -l | grep talvex_shop`
3. Test connection manually with same credentials
4. Restart application after fixing the issue

#### New Shop Creation Fails

**Symptoms**: Error when creating ShopProfile, no database created

**Causes**:
- PostgreSQL user lacks CREATE DATABASE permission
- Database name already exists
- Connection to PostgreSQL failed

**Recovery**:
1. Check error message in response
2. Verify PostgreSQL permissions: `GRANT CREATE ON DATABASE postgres TO your_user;`
3. Check if database already exists and clean up if needed
4. Retry shop creation

#### Shop Database Not Accessible After Restart

**Symptoms**: Shop worked before restart, now gets connection error

**Causes**:
- Database was deleted manually
- ShopProfile.database_name field is incorrect
- Registration failed at startup

**Recovery**:
1. Check if database exists in PostgreSQL
2. Verify ShopProfile.database_name matches actual database
3. Check startup logs for registration errors
4. Re-create database if needed using ShopDatabaseManager

### Debug Commands

```python
# Check current shop database context
from config.thread_local import get_current_shop_db
print(f"Current DB: {get_current_shop_db()}")

# List all configured databases
from django.conf import settings
print(f"Databases: {list(settings.DATABASES.keys())}")
```

## Production Considerations

1. **Connection Pooling**: Configure for multiple databases
2. **Database Limits**: Monitor PostgreSQL connection limits
3. **Backup Strategy**: Plan for per-database backups
4. **Monitoring**: Track database sizes and performance per shop
