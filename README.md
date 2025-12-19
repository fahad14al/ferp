This is the webapp link : https://fahadalmohammad.pythonanywhere.com/account/login/
username : fahadalmohammad50
password : mynamefahad

# FERP - Full Enterprise Resource Planning

FERP is a modern, lightweight Enterprise Resource Planning system built with Django.

## Features

- **Dashboard:** Real-time overview of business metrics.
- **Inventory Management:** Track products, categories, and stock movements.
- **Sales Management:** Create sales orders, manage customers, and generate invoices.
- **Point of Sale (POS):** Fast, interface for quick sales.
- **Reports:** Detailed business reports with Excel and PDF export.
- **Dynamic Settings:** Manage system-wide configurations like tax rates directly from the admin panel.

## Technology Stack

- **Backend:** Django 5.1
- **Frontend:** Vanilla CSS, JavaScript, Bootstrap 5
- **Database:** SQLite (default)
- **UI/UX:** Modern sidebar-based navigation with a focus on usability.

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/fahad14al/ferp.git
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Start the development server:
   ```bash
   python manage.py runserver
   ```
