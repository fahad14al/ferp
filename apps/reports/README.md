# Reports App

A comprehensive reporting module for the Django ERP system with advanced features including export capabilities, data visualizations, and modern responsive templates.

## Features

### 📊 Report Types
- **Purchase Summary**: Overview of purchase orders, suppliers, and spending
- **Supplier Performance**: Delivery times, quality ratings, and performance metrics
- **Inventory Turnover**: Product turnover rates and inventory efficiency
- **Sales vs Purchase Analysis**: Comparison of sales and purchase performance
- **Financial Summary**: Revenue, expenses, and profit analysis

### 📤 Export Formats
- PDF (requires WeasyPrint)
- Excel (requires openpyxl)
- CSV

### 📈 Visualizations
- Interactive Chart.js charts
- Responsive metric cards
- Color-coded performance indicators
- Progress bars and trend indicators

### 🎨 Modern UI
- Bootstrap 5 responsive design
- Gradient headers
- Hover effects and animations
- Print-friendly layouts
- Mobile-responsive

## Installation

1. Install dependencies:
```bash
pip install openpyxl weasyprint
```

2. Run migrations:
```bash
python manage.py makemigrations reports
python manage.py migrate
```

3. Access reports at: `http://localhost:8000/reports/`

## Usage

### Generating Reports
1. Navigate to Reports page
2. Select desired report
3. Apply filters (date range, supplier, etc.)
4. Choose export format or view in browser
5. Click "Apply Filters"

### Admin Management
Access Django admin to:
- Manage report templates
- View generated reports
- Track dashboard metrics
- Configure report settings

## Files Structure

```
apps/reports/
├── admin.py          # Admin configuration
├── forms.py          # Filter forms
├── models.py         # Report models
├── utils.py          # Export utilities
├── views.py          # Report views
└── urls.py           # URL routing

templates/reports/
├── report_list.html              # Dashboard
├── purchase_summary.html         # Purchase report
├── supplier_performance.html     # Supplier report
├── inventory_turnover.html       # Inventory report
├── sales_vs_purchase.html        # Sales vs Purchase
└── financial_summary.html        # Financial report
```

## Dependencies

- Django 5.1+
- openpyxl (Excel export)
- weasyprint (PDF export - optional)
- Chart.js (included via CDN)

## Notes

- WeasyPrint has system dependencies and may require additional setup
- If WeasyPrint is not installed, PDF export will show an error message
- All reports support date range filtering
- Export functionality is integrated into each report view
