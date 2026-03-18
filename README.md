# Talvex - Multi-Tenant Tailoring & Store Management System

A comprehensive Django-based management system for tailoring shops and stores, featuring a multi-tenant architecture where each shop has its own isolated database.

## 🚀 Getting Started (Setup for New PC)

Follow these steps to set up the project on a new machine.

### 1. Prerequisites

Ensure you have the following installed:
- **Python 3.8+**
- **PostgreSQL** (Ensure it's running and you have a user with `CREATE DATABASE` privileges)
- **Git**

### 2. Clone the Repository

```bash
git clone <repository-url>
cd talvex
```

### 3. Create a Virtual Environment

It is highly recommended to use a virtual environment to isolate project dependencies.

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Environment Configuration

Create a file named `.env` in the root directory (where `manage.py` is located) and add the following configuration:

```ini
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost

> **Note**: To generate a secure `SECRET_KEY`, you can run this command in your terminal after activating your virtual environment:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

# Database Connection Details
# Replace 'your_password' with your PostgreSQL password
DATABASE_URL=postgres://postgres:your_password@localhost:5432/talvex_main

# Individual DB fields (used by setup_databases.py script)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
```

### 6. Initialize the Databases

This project uses a special script to create the main database and run initial migrations.

```bash
python setup_databases.py
```

This script will:
1. Create the `talvex_main` database in PostgreSQL.
2. Run migrations for the main database (users, shop profiles, etc.).

### 7. Create a Superuser

To access the admin panel, you need a superuser account on the **main** database.

```bash
python manage.py createsuperuser --database=main
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

---

## 🏗️ Project Architecture

### Databases
- **Main Database (`talvex_main`)**: Stores global data like Users, Shop Profiles, and Django Sessions.
- **Shop Databases (`talvex_shop_{id}`)**: Each shop registered in the system gets its own isolated database for Customers, Products, Inventory, and Bills.

### Multi-Tenancy
The system automatically routes requests to the correct shop database based on the logged-in user's shop profile. 

- For technical details on the multi-tenant implementation, see [MULTI_TENANT_README.md](MULTI_TENANT_README.md).

## 🛠️ Common Commands

- **Run Migrations on Main DB**: `python manage.py migrate --database=main`
- **Create New App**: `python manage.py startapp <app_name>`
- **Check All Databases**: `python check_all_tables.py` (Custom script)

## 📁 Directory Structure

- `config/`: Project settings and database routing logic.
- `users/`: User management and multi-tenant registration.
- `customers/`: Shop-specific customer management.
- `store/`: Shop-specific inventory and billing.
- `templates/`: HTML templates for the frontend.
- `static/`: CSS, JavaScript, and image files.
