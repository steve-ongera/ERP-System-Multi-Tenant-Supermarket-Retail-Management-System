# ERP System - Multi-Tenant Supermarket & Retail Management System

A full-stack Enterprise Resource Planning (ERP) system for supermarkets, grocery stores and retail businesses in Kenya. The backend is a Django REST Framework API and the frontend is a React (Vite) single-page app. The system supports multi-tenancy, multiple branches, POS operations, inventory management and M-Pesa payments.

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Frontend Guide](#frontend-guide)
- [User Roles & Permissions](#user-roles--permissions)
- [Configuration](#configuration)
- [M-Pesa Integration](#m-pesa-integration)
- [Reports Available](#reports-available)
- [Security Features](#security-features)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Roadmap](#roadmap)

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
- SKU and barcode management, with a barcode lookup endpoint for scanners
- Multi-branch stock tracking
- Stock movements tracking (purchases, sales, returns, adjustments, transfers, damages, expiry)
- Batch tracking with expiry dates
- Low stock alerts and reorder levels
- Supplier management

#### 4. **Purchase Management**
- Purchase order creation and approval workflow
- Supplier management with credit limits
- Partial and full order receiving (stock is updated on receipt)
- Purchase order status tracking (Draft, Pending, Approved, Ordered, Received, Completed, Cancelled)

#### 5. **Sales & Point of Sale (POS)**
- Fast POS interface for quick checkouts
- Single-request checkout that deducts stock, applies promotions and records payments atomically
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
- Automatic payment confirmation through the Daraja callback

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

**Backend**
- Django 4.2 and Django REST Framework
- PostgreSQL (recommended) / MySQL / SQLite
- Token authentication with a custom User model
- Django FileField for uploads (supports S3/cloud storage)
- M-Pesa Daraja API
- Optional: Celery and Redis for background tasks and caching

**Frontend**
- React 18 with Vite
- React Router
- Axios for API calls

## Architecture

```
React (Vite)  --->  Django REST API  --->  PostgreSQL
 services/api.js     views.py              models.py
                      |
                      +-->  services.py  (business rules: stock, sales, M-Pesa, reports)
                      +-->  serializers.py (validation and JSON shape)
```

- **Views** handle HTTP, permissions and tenant scoping. Every query is filtered to the signed-in user's tenant, and branch-level staff only see their own branch.
- **Services** hold the business logic (checkout, stock adjustments, purchase receiving, shifts, M-Pesa, reports) so it stays in one place and runs inside database transactions.
- **Frontend** talks to the API only through `src/services/api.js`, which attaches the auth token and normalises errors.

## Prerequisites

- Python 3.8+ (3.10+ recommended)
- Node.js 18+ and npm
- PostgreSQL 12+ (recommended) or MySQL 8.0+
- Redis (for caching and Celery tasks - optional)
- Celery (for background tasks - optional)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/erp-system.git
cd erp-system
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Backend Environment Configuration

Create `backend/.env`:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (omit DB_ENGINE to use SQLite for quick local development)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=erp_system_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Frontend origins allowed to call the API
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# M-Pesa Settings
MPESA_ENVIRONMENT=sandbox  # or production
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=174379
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

# Optional
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
LOYALTY_KES_PER_POINT=100
EXPIRY_ALERT_DAYS=30
```

### 4. Database Setup

```bash
python manage.py makemigrations erp_system
python manage.py migrate
python manage.py createsuperuser
```

### 5. Load Initial Data (Optional)

```bash
python manage.py loaddata initial_data.json
```

### 6. Run the Backend

```bash
python manage.py runserver
```

- API: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`

### 7. Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000/api
```

Start the Vite dev server:

```bash
npm run dev
```

Open `http://localhost:5173` and sign in with a user that belongs to a tenant. The superuser you created in step 4 has no tenant, so first create a tenant, a branch and a tenant admin user in the Django admin.

## Project Structure

```
erp-system/
├── backend/
│   ├── config/
│   │   ├── settings.py        # Project settings (env-driven)
│   │   ├── urls.py            # Mounts the API at /api/
│   │   └── wsgi.py
│   ├── erp_system/
│   │   ├── models.py          # All database models
│   │   ├── admin.py           # Django admin configuration
│   │   ├── serializers.py     # DRF serializers and request validation
│   │   ├── services.py        # Business logic (stock, sales, M-Pesa, reports)
│   │   ├── views.py           # API viewsets and endpoints
│   │   ├── urls.py            # API routing
│   │   ├── signals.py         # Django signals
│   │   ├── utils.py           # Utility functions
│   │   ├── permissions.py     # Custom permissions
│   │   └── migrations/        # Database migrations
│   ├── media/                 # User uploaded files
│   ├── manage.py
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx           # React entry point, mounts the router
│       ├── App.jsx            # Routes, auth context, layout and pages
│       ├── index.css          # Base styles
│       └── services/
│           └── api.js         # Axios client and API helpers
└── README.md
```

## API Reference

All endpoints are under `/api/` and, except login and the M-Pesa callback, require the header `Authorization: Token <token>`. List endpoints are paginated (`{count, next, previous, results}`) and support `?search=`, `?ordering=` and field filters.

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login/` | Returns `{token, user}` |
| POST | `/auth/logout/` | Invalidates the token |
| GET | `/auth/me/` | Current user |

### Resources (standard list / create / retrieve / update / delete)

`branches`, `users`, `employees`, `categories`, `suppliers`, `products`, `customers`, `returns`, `expenses`, `promotions`, `purchase-orders`, `notifications`

Read-only: `sales`, `payments`, `stock-levels`, `stock-movements`, `audit-logs`, `mpesa/transactions`

### Custom actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products/lookup/?code=` | Find a product by barcode or SKU |
| POST | `/sales/checkout/` | Create a sale (items, payments, customer, promotion code) |
| POST | `/sales/{id}/void/` | Cancel a sale and restore stock (managers) |
| POST | `/stock/adjust/` | Add or remove stock with a movement record |
| POST | `/stock/transfer/` | Move stock between branches |
| GET | `/stock/expiring/` | Batches expiring soon |
| GET | `/stock-levels/low/` | Items at or below reorder level |
| POST | `/purchase-orders/{id}/approve/` | Approve a purchase order |
| POST | `/purchase-orders/{id}/receive/` | Receive goods (partial or full) |
| GET | `/shifts/current/` | The cashier's open shift |
| POST | `/shifts/` | Open a shift |
| POST | `/shifts/{id}/close/` | Close a shift and compute variance |
| POST | `/mpesa/stk-push/` | Send an STK prompt to a customer |
| GET | `/mpesa/status/{checkout_request_id}/` | Poll payment status |
| POST | `/mpesa/callback/` | Public Daraja callback |
| GET/PUT | `/settings/` | Tenant settings |

### Reports

`GET /reports/dashboard/`, `/reports/daily-sales/`, `/reports/sales-trend/`, `/reports/top-products/`, `/reports/sales-by-category/`, `/reports/profit-loss/`, `/reports/inventory-valuation/`, `/reports/top-customers/`

Date-range reports accept `?start=YYYY-MM-DD&end=YYYY-MM-DD`.

### Example: checkout

```json
POST /api/sales/checkout/
{
  "branch": 1,
  "customer": 12,
  "items": [{ "product": 5, "quantity": "2" }],
  "payments": [{ "method": "cash", "amount": "300.00" }],
  "promotion_code": "WEEKEND10"
}
```

## Frontend Guide

- `src/services/api.js` exports an Axios instance plus helpers grouped by area (`productsApi`, `salesApi`, `mpesaApi`, `reportsApi` and so on). It stores the token in `localStorage`, adds it to every request, and signs the user out when the API returns 401.
- `errorMessage(error)` converts any API error into a single readable string, and `unwrap(data)` handles both paginated and plain list responses.
- `App.jsx` defines the routes, an `AuthProvider`, a protected layout with sidebar navigation, and the pages: Dashboard, Point of Sale, Sales, Products, Inventory, Customers, Suppliers, Expenses, Promotions and Shifts.
- M-Pesa at the POS: checkout saves the sale as pending, `mpesaApi.stkPush` prompts the customer, and `mpesaApi.waitForPayment` polls until the callback marks the payment successful, failed or cancelled.
- Build for production with `npm run build`; the output is in `frontend/dist`.

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
4. Set `MPESA_CALLBACK_URL` in `backend/.env` to a public HTTPS URL that points to `/api/mpesa/callback/`
5. Enable M-Pesa in Tenant Settings

During local development, expose your backend with a tunnelling tool (for example ngrok) so Safaricom can reach the callback.

### Testing

Use Safaricom sandbox credentials for testing:
- Shortcode: `174379`
- Test phone: `254708374149`

Phone numbers are normalised automatically, so `0712345678`, `+254712345678` and `254712345678` are all accepted.

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
- Token authentication and per-tenant data isolation on every endpoint
- Role-based write permissions
- CSRF protection and a CORS allow-list
- SQL injection prevention through ORM
- XSS protection
- Request throttling
- Audit logging of all critical actions
- IP address tracking
- Session security
- HTTPS, secure cookies and HSTS enforced when `DEBUG=False`

## Testing

```bash
cd backend

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
- [ ] Set `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to your real domains
- [ ] Set up PostgreSQL/MySQL database
- [ ] Run `python manage.py collectstatic` and configure static file serving (nginx/whitenoise)
- [ ] Build the frontend (`npm run build`) and serve `frontend/dist` from nginx or a CDN
- [ ] Set `VITE_API_URL` to the production API URL before building
- [ ] Set up media file storage (S3/Cloud Storage)
- [ ] Configure HTTPS
- [ ] Set up backup strategy
- [ ] Configure email service
- [ ] Set up monitoring and logging
- [ ] Configure Celery for background tasks
- [ ] Set up Redis for caching
- [ ] Switch `MPESA_ENVIRONMENT` to `production` with live credentials

### Recommended Deployment Stack

- **Server:** Ubuntu 20.04+ LTS
- **Web Server:** Nginx (serves the React build and proxies `/api/` to Gunicorn)
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
- Django REST Framework
- React and Vite
- Safaricom Daraja API
- All open-source libraries used in this project

---

**Made for Kenyan retailers**