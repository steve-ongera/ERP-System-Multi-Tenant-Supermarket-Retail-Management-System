# ERP System - Multi-Tenant Supermarket & Retail Management System

A comprehensive Enterprise Resource Planning (ERP) system built with Django, designed specifically for supermarkets, grocery stores, and retail businesses in Kenya. The system supports multi-tenancy, multiple branches, POS operations, inventory management, and M-Pesa integration.

## Features

### Core Modules

#### 1. **Multi-Tenant Architecture**
- Support for multiple independent businesses (tenants)
- Each tenant can have multiple branches
- Isolated data and customizable settings per tenant
- Subscription-based plans (Trial, Basic, Standard, Premium, Enterprise)

#### 2. **User Management**
- Role-based access control (RBAC)
- User types: Super Admin, Tenant Admin, Branch Manager, Cashier, Inventory Manager, Sales Staff, Accountant
- Employee management with salary tracking
- Audit trail for all user actions

#### 3. **Inventory Management**
- Product catalog with categories and subcategories
- SKU and barcode management
- Multi-branch stock tracking
- Stock movements tracking (purchases, sales, returns, adjustments, transfers, damages, expiry)
- Batch tracking with expiry dates
- Low stock alerts and reorder levels
- Supplier management

#### 4. **Purchase Management**
- Purchase order creation and approval workflow
- Supplier management with credit limits
- Partial and full order receiving
- Purchase order status tracking (Draft, Pending, Approved, Ordered, Received, Completed, Cancelled)

#### 5. **Sales & Point of Sale (POS)**
- Fast POS interface for quick checkouts
- Invoice generation
- Customer management (Retail, Wholesale, VIP)
- Multiple payment methods (Cash, M-Pesa, Card, Bank Transfer, Credit, Cheque)
- Loyalty points program
- Discount management

#### 6. **Payment Processing**
- Multiple payment methods support
- M-Pesa STK Push integration
- Split payments support
- Payment history tracking

#### 7. **Returns & Refunds**
- Product return management
- Multiple return reasons (defective, wrong item, expired, etc.)
- Refund processing (Cash, M-Pesa, Store Credit)
- Return approval workflow

#### 8. **Expense Management**
- Expense categorization
- Receipt attachment support
- Branch-wise expense tracking
- Payment method tracking

#### 9. **Shift Management**
- Cashier shift tracking
- Opening and closing cash management
- Cash reconciliation
- Shift variance reporting

#### 10. **Promotions & Discounts**
- Percentage and fixed amount discounts
- Buy X Get Y promotions
- Product and category-based promotions
- Time-bound promotions
- Usage limit tracking

#### 11. **Reports & Analytics**
- Daily sales summaries
- Profit and loss reports
- Inventory reports
- Low stock reports
- Sales by product/category
- Payment method analysis

#### 12. **M-Pesa Integration**
- STK Push for customer payments
- Transaction logging and reconciliation
- Sandbox and production environment support
- Automatic payment confirmation

#### 13. **Notifications**
- Low stock alerts
- Product expiry alerts
- Sale notifications
- Payment confirmations
- System notifications

#### 14. **Audit & Compliance**
- Comprehensive audit logs
- User action tracking
- IP address and user agent logging
- Change history with JSON storage
- KRA PIN/Tax ID management

## Technology Stack

- **Backend:** Django 4.x
- **Database:** PostgreSQL (recommended) / MySQL / SQLite
- **Authentication:** Django Auth with custom User model
- **File Storage:** Django FileField (supports S3/cloud storage)
- **Payment:** M-Pesa Daraja API

## Prerequisites

- Python 3.8+
- Django 4.0+
- PostgreSQL 12+ (recommended) or MySQL 8.0+
- Redis (for caching and Celery tasks - optional)
- Celery (for background tasks - optional)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/erp-system.git
cd erp-system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=erp_system_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# M-Pesa Settings
MPESA_ENVIRONMENT=sandbox  # or production
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=your_shortcode
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/api/mpesa/callback/

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password

# SMS Settings (optional)
SMS_API_KEY=your_sms_api_key
SMS_SENDER_ID=your_sender_id

# Static & Media Files
STATIC_URL=/static/
MEDIA_URL=/media/
```

### 5. Database Setup

```bash
# Create database
python manage.py makemigrations erp_system
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Load Initial Data (Optional)

```bash
python manage.py loaddata initial_data.json
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Visit: `http://localhost:8000/admin/`

## Project Structure

```
erp_system/
├── erp_system/
│   ├── __init__.py
│   ├── models.py          # All database models
│   ├── admin.py           # Django admin configuration
│   ├── views.py           # API/Views
│   ├── serializers.py     # DRF serializers (if using REST API)
│   ├── urls.py            # URL routing
│   ├── signals.py         # Django signals
│   ├── utils.py           # Utility functions
│   ├── permissions.py     # Custom permissions
│   └── migrations/        # Database migrations
├── static/                # Static files (CSS, JS, images)
├── media/                 # User uploaded files
├── templates/             # HTML templates
├── requirements.txt       # Python dependencies
├── manage.py
└── README.md
```

## User Roles & Permissions

### Super Admin
- Full system access
- Manage all tenants
- System configuration

### Tenant Admin
- Full access to their tenant
- Manage branches and users
- Configure tenant settings
- View all reports

### Branch Manager
- Manage assigned branch
- Approve purchase orders
- View branch reports
- Manage staff

### Inventory Manager
- Manage products and stock
- Create purchase orders
- Track stock movements
- Manage suppliers

### Cashier
- Process sales
- Handle payments
- Manage shifts
- Process returns

### Accountant
- View financial reports
- Manage expenses
- Reconcile payments
- Generate invoices

### Sales Staff
- Create sales
- Manage customers
- Process orders

## Configuration

### Tenant Settings

Each tenant can configure:
- Tax rates and tax numbers
- Receipt header/footer
- M-Pesa integration details
- Loyalty program settings
- Email/SMS notifications
- Inventory rules (negative stock, auto-decrease)
- Invoice numbering

### Branch Setup

1. Create tenant
2. Add branches
3. Assign users to branches
4. Configure branch-specific settings

## M-Pesa Integration

### Setup Steps

1. Register for Safaricom Daraja API
2. Get Consumer Key and Consumer Secret
3. Configure shortcode and passkey
4. Set callback URL in `.env`
5. Enable M-Pesa in Tenant Settings

### Testing

Use Safaricom sandbox credentials for testing:
- Shortcode: `174379`
- Test phone: `254708374149`

## Reports Available

1. **Sales Reports**
   - Daily sales summary
   - Sales by product
   - Sales by category
   - Sales by payment method

2. **Inventory Reports**
   - Current stock levels
   - Low stock items
   - Expiring products
   - Stock movement history

3. **Financial Reports**
   - Profit & Loss
   - Revenue analysis
   - Expense tracking
   - Payment reconciliation

4. **Customer Reports**
   - Top customers
   - Customer purchase history
   - Loyalty points tracking

## Security Features

- Password hashing with Django's PBKDF2
- CSRF protection
- SQL injection prevention through ORM
- XSS protection
- Audit logging of all critical actions
- IP address tracking
- Session security

## Testing

```bash
# Run all tests
python manage.py test erp_system

# Run specific test
python manage.py test erp_system.tests.TestProductModel

# Run with coverage
coverage run --source='.' manage.py test erp_system
coverage report
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up PostgreSQL/MySQL database
- [ ] Configure static file serving (nginx/whitenoise)
- [ ] Set up media file storage (S3/Cloud Storage)
- [ ] Configure HTTPS
- [ ] Set up backup strategy
- [ ] Configure email service
- [ ] Set up monitoring and logging
- [ ] Configure Celery for background tasks
- [ ] Set up Redis for caching

### Recommended Deployment Stack

- **Server:** Ubuntu 20.04+ LTS
- **Web Server:** Nginx
- **WSGI:** Gunicorn
- **Database:** PostgreSQL
- **Cache:** Redis
- **Task Queue:** Celery with Redis
- **Monitoring:** Sentry
- **SSL:** Let's Encrypt

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Email: support@yourcompany.com
- Documentation: https://docs.yourcompany.com
- Issues: https://github.com/yourusername/erp-system/issues

## Roadmap

- [ ] Mobile app (React Native)
- [ ] WhatsApp integration for notifications
- [ ] Advanced analytics dashboard
- [ ] Multi-currency support
- [ ] E-commerce integration
- [ ] Delivery management
- [ ] Employee attendance tracking
- [ ] Payroll integration
- [ ] Customer portal
- [ ] Supplier portal

## Screenshots

*Add screenshots of your application here*

## Acknowledgments

- Django Framework
- Safaricom Daraja API
- All open-source libraries used in this project

---

**Made for Kenyan retailers**