from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


# ============================================
# TENANT & ORGANIZATION MANAGEMENT
# ============================================

class Tenant(models.Model):
    """Main tenant model - each supermarket/retail store is a tenant"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    business_type = models.CharField(max_length=100, choices=[
        ('supermarket', 'Supermarket'),
        ('grocery', 'Grocery Store'),
        ('retail', 'Retail Store'),
        ('pharmacy', 'Pharmacy'),
        ('general', 'General Store')
    ], default='supermarket')
    
    # Business Details
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="KRA PIN")
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    
    # Address
    physical_address = models.TextField()
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Subscription & Status
    subscription_plan = models.CharField(max_length=50, choices=[
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise')
    ], default='trial')
    subscription_start = models.DateTimeField(auto_now_add=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Configuration
    currency = models.CharField(max_length=3, default='KES')
    timezone = models.CharField(max_length=50, default='Africa/Nairobi')
    
    # Branding
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#007bff')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.business_name


class Branch(models.Model):
    """Multiple branches for a tenant"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    
    # Contact
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    physical_address = models.TextField()
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    
    is_main_branch = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'branches'
        unique_together = [['tenant', 'code']]
        verbose_name_plural = 'Branches'
    
    def __str__(self):
        return f"{self.tenant.business_name} - {self.name}"


# ============================================
# USER MANAGEMENT
# ============================================

class User(AbstractUser):
    """Custom user model supporting multi-tenant with roles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    USER_TYPES = [
        ('super_admin', 'Super Admin'),  # System owner
        ('tenant_admin', 'Tenant Admin'),  # Supermarket owner/manager
        ('branch_manager', 'Branch Manager'),
        ('cashier', 'Cashier'),
        ('inventory_manager', 'Inventory Manager'),
        ('sales_staff', 'Sales Staff'),
        ('accountant', 'Accountant'),
    ]
    
    user_type = models.CharField(max_length=50, choices=USER_TYPES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Employment
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Profile
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"


# ============================================
# INVENTORY MANAGEMENT
# ============================================

class Category(models.Model):
    """Product categories"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        unique_together = [['tenant', 'slug']]
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Suppliers/Vendors"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    
    # Contact
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers'
        unique_together = [['tenant', 'code']]
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Products/Items for sale"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Basic Info
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    description = models.TextField(blank=True, null=True)
    
    # Pricing
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Tax
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=16, help_text="VAT percentage")
    is_tax_inclusive = models.BooleanField(default=True)
    
    # Inventory
    unit_of_measure = models.CharField(max_length=50, choices=[
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('liter', 'Liter'),
        ('ml', 'Milliliter'),
        ('pack', 'Pack'),
        ('box', 'Box'),
        ('carton', 'Carton'),
    ], default='piece')
    
    reorder_level = models.IntegerField(default=10, help_text="Minimum stock level before reorder")
    reorder_quantity = models.IntegerField(default=50, help_text="Quantity to order when restocking")
    
    # Product Details
    brand = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    
    # Images
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    track_inventory = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def final_price(self):
        """Calculate final price after discount"""
        discount_amount = self.selling_price * (self.discount_percentage / 100)
        return self.selling_price - discount_amount


class Stock(models.Model):
    """Stock levels per branch"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stocks')
    
    quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0, help_text="Quantity in pending orders")
    
    last_restocked = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stocks'
        unique_together = [['product', 'branch']]
    
    def __str__(self):
        return f"{self.product.name} - {self.branch.name}: {self.quantity}"
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity


class StockMovement(models.Model):
    """Track all stock movements"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_movements')
    
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('damage', 'Damage/Loss'),
        ('expiry', 'Expiry'),
    ]
    
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_type} - {self.product.name}: {self.quantity}"


# ============================================
# PURCHASE MANAGEMENT
# ============================================

class PurchaseOrder(models.Model):
    """Purchase orders to suppliers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='purchase_orders')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    
    po_number = models.CharField(max_length=100, unique=True)
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
        ('received', 'Partially Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PO-{self.po_number}"


class PurchaseOrderItem(models.Model):
    """Items in a purchase order"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_items')
    
    quantity_ordered = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_received = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_order_items'
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_ordered} units"


# ============================================
# CUSTOMER MANAGEMENT
# ============================================

class Customer(models.Model):
    """Customer/Client management"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='customers')
    
    # Basic Info
    customer_code = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial
    customer_type = models.CharField(max_length=50, choices=[
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('vip', 'VIP'),
    ], default='retail')
    
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loyalty_points = models.IntegerField(default=0)
    
    # Dates
    date_of_birth = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        unique_together = [['tenant', 'customer_code']]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.customer_code})"


# ============================================
# SALES & POS
# ============================================

class Sale(models.Model):
    """Sales/Invoices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='sales')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    
    invoice_number = models.CharField(max_length=100, unique=True)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_given = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS, default='pending')
    
    SALE_TYPE = [
        ('pos', 'POS'),
        ('invoice', 'Invoice'),
        ('quote', 'Quote'),
    ]
    
    sale_type = models.CharField(max_length=50, choices=SALE_TYPE, default='pos')
    
    notes = models.TextField(blank=True, null=True)
    
    sale_date = models.DateTimeField(default=timezone.now)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sales'
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"Sale-{self.invoice_number}"


class SaleItem(models.Model):
    """Items in a sale"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sale_items'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Payment(models.Model):
    """Payment transactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='payments')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    transaction_id = models.CharField(max_length=100, unique=True)
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit', 'Credit'),
        ('cheque', 'Cheque'),
    ]
    
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # M-Pesa specific
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    mpesa_phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Card specific
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    
    payment_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment-{self.transaction_id}"


# ============================================
# EXPENSES & ACCOUNTING
# ============================================

class ExpenseCategory(models.Model):
    """Categories for expenses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'expense_categories'
        verbose_name_plural = 'Expense Categories'
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Business expenses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='expenses')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses')
    
    reference_number = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    
    expense_date = models.DateField(default=timezone.now)
    
    # Supporting documents
    receipt_image = models.ImageField(upload_to='expense_receipts/', blank=True, null=True)
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ]
    
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    paid_to = models.CharField(max_length=255)
    
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='expenses')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']
    
    def __str__(self):
        return f"{self.reference_number} - {self.description}"


# ============================================
# REPORTS & ANALYTICS
# ============================================

class DailySummary(models.Model):
    """Daily sales and operations summary per branch"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='daily_summaries')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='daily_summaries')
    
    date = models.DateField()
    
    # Sales
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_transactions = models.IntegerField(default=0)
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mpesa_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Refunds
    total_refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_transactions = models.IntegerField(default=0)
    
    # Expenses
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Profit
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Inventory
    products_sold = models.IntegerField(default=0)
    low_stock_items = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_summaries'
        unique_together = [['tenant', 'branch', 'date']]
        ordering = ['-date']
        verbose_name_plural = 'Daily Summaries'
    
    def __str__(self):
        return f"{self.branch.name} - {self.date}"


# ============================================
# NOTIFICATIONS & ALERTS
# ============================================

class Notification(models.Model):
    """System notifications for users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    NOTIFICATION_TYPES = [
        ('low_stock', 'Low Stock Alert'),
        ('sale', 'Sale Notification'),
        ('purchase', 'Purchase Notification'),
        ('payment', 'Payment Notification'),
        ('system', 'System Notification'),
        ('expiry', 'Product Expiry Alert'),
    ]
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Reference
    reference_id = models.UUIDField(null=True, blank=True)
    reference_model = models.CharField(max_length=100, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


# ============================================
# AUDIT & LOGS
# ============================================

class AuditLog(models.Model):
    """Audit trail for all important actions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    model_name = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True, blank=True)
    
    description = models.TextField()
    
    # Technical details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Changes (JSON)
    changes = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.model_name} by {self.user}"


# ============================================
# SETTINGS & CONFIGURATION
# ============================================

class TenantSettings(models.Model):
    """Tenant-specific settings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='settings')
    
    # POS Settings
    enable_loyalty_program = models.BooleanField(default=False)
    loyalty_points_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, help_text="Points per currency unit")
    
    # Tax Settings
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    tax_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Receipt Settings
    receipt_header = models.TextField(blank=True, null=True)
    receipt_footer = models.TextField(blank=True, null=True)
    show_logo_on_receipt = models.BooleanField(default=True)
    
    # M-Pesa Settings
    mpesa_enabled = models.BooleanField(default=False)
    mpesa_shortcode = models.CharField(max_length=20, blank=True, null=True)
    mpesa_consumer_key = models.CharField(max_length=255, blank=True, null=True)
    mpesa_consumer_secret = models.CharField(max_length=255, blank=True, null=True)
    mpesa_passkey = models.TextField(blank=True, null=True)
    mpesa_environment = models.CharField(max_length=20, choices=[
        ('sandbox', 'Sandbox'),
        ('production', 'Production')
    ], default='sandbox')
    
    # Email Settings
    enable_email_notifications = models.BooleanField(default=False)
    notification_email = models.EmailField(blank=True, null=True)
    
    # SMS Settings
    enable_sms_notifications = models.BooleanField(default=False)
    sms_sender_id = models.CharField(max_length=11, blank=True, null=True)
    
    # Inventory Settings
    auto_decrease_stock = models.BooleanField(default=True)
    allow_negative_stock = models.BooleanField(default=False)
    enable_low_stock_alerts = models.BooleanField(default=True)
    
    # Invoice Settings
    invoice_prefix = models.CharField(max_length=10, default='INV')
    invoice_starting_number = models.IntegerField(default=1000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenant_settings'
        verbose_name_plural = 'Tenant Settings'
    
    def __str__(self):
        return f"Settings for {self.tenant.business_name}"


# ============================================
# PROMOTIONS & DISCOUNTS
# ============================================

class Promotion(models.Model):
    """Promotional campaigns and discounts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='promotions')
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('buy_x_get_y', 'Buy X Get Y'),
    ]
    
    discount_type = models.CharField(max_length=50, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Buy X Get Y specifics
    buy_quantity = models.IntegerField(null=True, blank=True)
    get_quantity = models.IntegerField(null=True, blank=True)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Constraints
    minimum_purchase_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    maximum_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total times this promotion can be used")
    usage_count = models.IntegerField(default=0)
    
    # Applicable products (many-to-many through intermediate table)
    applicable_products = models.ManyToManyField(Product, blank=True, related_name='promotions')
    applicable_categories = models.ManyToManyField(Category, blank=True, related_name='promotions')
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'promotions'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


# ============================================
# RETURNS & REFUNDS
# ============================================

class Return(models.Model):
    """Product returns and refunds"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='returns')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='returns')
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns')
    
    return_number = models.CharField(max_length=100, unique=True)
    
    RETURN_REASONS = [
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item'),
        ('expired', 'Expired Product'),
        ('customer_changed_mind', 'Customer Changed Mind'),
        ('damaged', 'Damaged in Transit'),
        ('other', 'Other'),
    ]
    
    reason = models.CharField(max_length=50, choices=RETURN_REASONS)
    notes = models.TextField(blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    REFUND_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('store_credit', 'Store Credit'),
        ('original_method', 'Original Payment Method'),
    ]
    
    refund_method = models.CharField(max_length=50, choices=REFUND_METHODS)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    return_date = models.DateTimeField(default=timezone.now)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='returns_created')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns_approved')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'returns'
        ordering = ['-return_date']
    
    def __str__(self):
        return f"Return-{self.return_number}"


class ReturnItem(models.Model):
    """Items in a return"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name='return_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='return_items')
    
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    ITEM_CONDITION = [
        ('unopened', 'Unopened'),
        ('opened', 'Opened'),
        ('damaged', 'Damaged'),
        ('defective', 'Defective'),
    ]
    
    condition = models.CharField(max_length=50, choices=ITEM_CONDITION)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'return_items'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# ============================================
# SHIFTS & CASH MANAGEMENT
# ============================================

class Shift(models.Model):
    """Cash register shifts for cashiers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='shifts')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='shifts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shifts')
    
    shift_number = models.CharField(max_length=100)
    
    # Opening
    opening_time = models.DateTimeField(default=timezone.now)
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2)
    opening_notes = models.TextField(blank=True, null=True)
    
    # Closing
    closing_time = models.DateTimeField(null=True, blank=True)
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    closing_notes = models.TextField(blank=True, null=True)
    
    # Expected vs Actual
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cash_difference = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Sales Summary
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_transactions = models.IntegerField(default=0)
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mpesa_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    is_closed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shifts'
        ordering = ['-opening_time']
    
    def __str__(self):
        return f"Shift-{self.shift_number} - {self.user.username}"


# ============================================
# M-PESA TRANSACTIONS
# ============================================

class MpesaTransaction(models.Model):
    """M-Pesa transaction logs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='mpesa_transactions')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='mpesa_transactions')
    
    # M-Pesa Details
    merchant_request_id = models.CharField(max_length=100, unique=True)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    TRANSACTION_TYPES = [
        ('stk_push', 'STK Push'),
        ('c2b', 'Customer to Business'),
        ('b2c', 'Business to Customer'),
    ]
    
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES, default='stk_push')
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Response data
    result_code = models.CharField(max_length=10, blank=True, null=True)
    result_description = models.TextField(blank=True, null=True)
    
    # Raw callback data
    callback_data = models.JSONField(null=True, blank=True)
    
    transaction_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mpesa_transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"M-Pesa-{self.merchant_request_id}"


# ============================================
# PRODUCT BATCHES & EXPIRY
# ============================================

class ProductBatch(models.Model):
    """Track product batches with expiry dates"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='product_batches')
    
    batch_number = models.CharField(max_length=100)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    
    is_expired = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_batches'
        verbose_name_plural = 'Product Batches'
        ordering = ['expiry_date']
    
    def __str__(self):
        return f"{self.product.name} - Batch {self.batch_number}"