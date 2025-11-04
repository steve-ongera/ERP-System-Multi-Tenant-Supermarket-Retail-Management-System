
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Tenant, Branch, User, Category, Supplier, Product, Stock, StockMovement,
    PurchaseOrder, PurchaseOrderItem, Customer, Sale, SaleItem, Payment,
    ExpenseCategory, Expense, DailySummary, Notification, AuditLog,
    TenantSettings, Promotion, Return, ReturnItem, Shift, MpesaTransaction,
    ProductBatch
)


# ============================================
# INLINE ADMIN CLASSES
# ============================================

class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ('name', 'code', 'city', 'is_main_branch', 'is_active')


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ('product', 'quantity_ordered', 'quantity_received', 'unit_price', 'subtotal')
    readonly_fields = ('subtotal',)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'discount_percentage', 'tax_percentage', 'subtotal')
    readonly_fields = ('subtotal',)


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'condition', 'subtotal')
    readonly_fields = ('subtotal',)


class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = ('branch', 'quantity', 'reserved_quantity', 'available_quantity')
    readonly_fields = ('available_quantity',)


class ProductBatchInline(admin.TabularInline):
    model = ProductBatch
    extra = 0
    fields = ('batch_number', 'quantity', 'expiry_date', 'is_expired')
    readonly_fields = ('is_expired',)


# ============================================
# TENANT & ORGANIZATION
# ============================================

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'business_type', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('business_type', 'subscription_plan', 'is_active', 'created_at')
    search_fields = ('business_name', 'email', 'phone', 'tax_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [BranchInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'business_name', 'slug', 'business_type')
        }),
        ('Business Details', {
            'fields': ('registration_number', 'tax_id', 'phone', 'email', 'website')
        }),
        ('Address', {
            'fields': ('physical_address', 'city', 'county', 'postal_code')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_start', 'subscription_end', 'is_active')
        }),
        ('Configuration', {
            'fields': ('currency', 'timezone')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'code', 'city', 'is_main_branch', 'is_active')
    list_filter = ('tenant', 'is_main_branch', 'is_active', 'city')
    search_fields = ('name', 'code', 'phone', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'name', 'code')
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Address', {
            'fields': ('physical_address', 'city', 'county')
        }),
        ('Status', {
            'fields': ('is_main_branch', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# USER MANAGEMENT
# ============================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'user_type', 'tenant', 'branch', 'is_active')
    list_filter = ('user_type', 'is_active', 'is_staff', 'tenant', 'branch')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'employee_id')
    readonly_fields = ('id', 'last_login', 'date_joined', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'username', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'id_number', 'date_of_birth', 'address', 'profile_picture')
        }),
        ('Organization', {
            'fields': ('tenant', 'branch', 'user_type')
        }),
        ('Employment', {
            'fields': ('employee_id', 'hire_date', 'salary')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'last_login_ip', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Account Information', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Organization', {
            'fields': ('tenant', 'branch', 'user_type')
        }),
    )


# ============================================
# INVENTORY MANAGEMENT
# ============================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'parent', 'is_active', 'created_at')
    list_filter = ('tenant', 'is_active', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'tenant', 'phone', 'email', 'current_balance', 'is_active')
    list_filter = ('tenant', 'is_active', 'city')
    search_fields = ('name', 'code', 'phone', 'email', 'contact_person')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'name', 'code')
        }),
        ('Contact', {
            'fields': ('contact_person', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address', 'city')
        }),
        ('Financial', {
            'fields': ('tax_id', 'payment_terms', 'credit_limit', 'current_balance')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'cost_price', 'selling_price', 'final_price_display', 'is_active', 'track_inventory')
    list_filter = ('tenant', 'category', 'is_active', 'is_featured', 'track_inventory', 'unit_of_measure')
    search_fields = ('name', 'sku', 'barcode', 'brand', 'manufacturer')
    readonly_fields = ('id', 'final_price_display', 'created_at', 'updated_at')
    inlines = [StockInline, ProductBatchInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'name', 'sku', 'barcode', 'description')
        }),
        ('Classification', {
            'fields': ('category', 'supplier', 'brand', 'manufacturer')
        }),
        ('Pricing', {
            'fields': ('cost_price', 'selling_price', 'discount_percentage', 'final_price_display')
        }),
        ('Tax', {
            'fields': ('tax_percentage', 'is_tax_inclusive')
        }),
        ('Inventory', {
            'fields': ('unit_of_measure', 'reorder_level', 'reorder_quantity', 'track_inventory')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def final_price_display(self, obj):
        return f"{obj.tenant.currency} {obj.final_price:,.2f}"
    final_price_display.short_description = 'Final Price'


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'branch', 'quantity', 'reserved_quantity', 'available_quantity_display', 'last_restocked')
    list_filter = ('branch', 'last_restocked')
    search_fields = ('product__name', 'product__sku', 'branch__name')
    readonly_fields = ('id', 'available_quantity_display', 'created_at', 'updated_at')
    
    def available_quantity_display(self, obj):
        available = obj.available_quantity
        if available <= 0:
            return format_html('<span style="color: red; font-weight: bold;">OUT OF STOCK</span>')
        elif available <= obj.product.reorder_level:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', available)
        return available
    available_quantity_display.short_description = 'Available Quantity'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'branch', 'movement_type', 'quantity', 'unit_cost', 'created_by', 'created_at')
    list_filter = ('movement_type', 'branch', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reference_number')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


# ============================================
# PURCHASE MANAGEMENT
# ============================================

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'tenant', 'branch', 'supplier', 'status', 'total_amount', 'order_date', 'expected_delivery_date')
    list_filter = ('status', 'tenant', 'branch', 'order_date')
    search_fields = ('po_number', 'supplier__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [PurchaseOrderItemInline]
    date_hierarchy = 'order_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'branch', 'supplier', 'po_number', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery_date', 'actual_delivery_date')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Approval', {
            'fields': ('created_by', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'product', 'quantity_ordered', 'quantity_received', 'unit_price', 'subtotal')
    list_filter = ('purchase_order__status',)
    search_fields = ('product__name', 'purchase_order__po_number')
    readonly_fields = ('id', 'created_at', 'updated_at')


# ============================================
# CUSTOMER MANAGEMENT
# ============================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_code', 'first_name', 'last_name', 'phone', 'customer_type', 'current_balance', 'loyalty_points', 'is_active')
    list_filter = ('tenant', 'customer_type', 'is_active', 'city')
    search_fields = ('customer_code', 'first_name', 'last_name', 'phone', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'customer_code', 'first_name', 'last_name', 'phone', 'email', 'date_of_birth')
        }),
        ('Address', {
            'fields': ('address', 'city')
        }),
        ('Financial', {
            'fields': ('customer_type', 'credit_limit', 'current_balance', 'loyalty_points')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# SALES & POS
# ============================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'branch', 'customer', 'total_amount', 'payment_status', 'sale_type', 'sale_date', 'created_by')
    list_filter = ('payment_status', 'sale_type', 'branch', 'sale_date')
    search_fields = ('invoice_number', 'receipt_number', 'customer__first_name', 'customer__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [SaleItemInline]
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'tenant', 'branch', 'customer', 'invoice_number', 'receipt_number', 'sale_type')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid', 'change_given', 'payment_status')
        }),
        ('Additional Information', {
            'fields': ('notes', 'sale_date')
        }),
        ('Created By', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price', 'discount_percentage', 'subtotal')
    list_filter = ('sale__sale_date',)
    search_fields = ('product__name', 'sale__invoice_number')
    readonly_fields = ('id', 'created_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'sale', 'payment_method', 'amount', 'payment_date', 'created_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('transaction_id', 'mpesa_receipt_number', 'sale__invoice_number')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'payment_date'


# ============================================
# EXPENSES & ACCOUNTING
# ============================================

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_active', 'created_at')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'category', 'branch', 'amount', 'payment_method', 'paid_to', 'expense_date', 'created_by')
    list_filter = ('category', 'payment_method', 'branch', 'expense_date')
    search_fields = ('reference_number', 'description', 'paid_to')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'expense_date'


# ============================================
# REPORTS & ANALYTICS
# ============================================

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'branch', 'total_sales', 'total_transactions', 'total_expenses', 'net_profit')
    list_filter = ('branch', 'date')
    search_fields = ('branch__name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'date'


# ============================================
# NOTIFICATIONS & SYSTEM
# ============================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'model_name', 'user', 'tenant', 'ip_address', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('description', 'user__username', 'model_name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


# ============================================
# SETTINGS & CONFIGURATION
# ============================================

@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'enable_loyalty_program', 'default_tax_rate', 'mpesa_enabled', 'auto_decrease_stock')
    list_filter = ('enable_loyalty_program', 'mpesa_enabled', 'auto_decrease_stock')
    search_fields = ('tenant__business_name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Tenant', {
            'fields': ('id', 'tenant')
        }),
        ('POS Settings', {
            'fields': ('enable_loyalty_program', 'loyalty_points_rate')
        }),
        ('Tax Settings', {
            'fields': ('default_tax_rate', 'tax_number')
        }),
        ('Receipt Settings', {
            'fields': ('receipt_header', 'receipt_footer', 'show_logo_on_receipt')
        }),
        ('M-Pesa Settings', {
            'fields': ('mpesa_enabled', 'mpesa_shortcode', 'mpesa_consumer_key', 'mpesa_consumer_secret', 'mpesa_passkey', 'mpesa_environment')
        }),
        ('Notification Settings', {
            'fields': ('enable_email_notifications', 'notification_email', 'enable_sms_notifications', 'sms_sender_id')
        }),
        ('Inventory Settings', {
            'fields': ('auto_decrease_stock', 'allow_negative_stock', 'enable_low_stock_alerts')
        }),
        ('Invoice Settings', {
            'fields': ('invoice_prefix', 'invoice_starting_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# PROMOTIONS & DISCOUNTS
# ============================================

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'discount_type', 'discount_value', 'start_date', 'end_date', 'is_active', 'usage_count')
    list_filter = ('discount_type', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'usage_count', 'created_at', 'updated_at')
    filter_horizontal = ('applicable_products', 'applicable_categories')


# ============================================
# RETURNS & REFUNDS
# ============================================

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'sale', 'customer', 'reason', 'status', 'refund_amount', 'return_date')
    list_filter = ('status', 'reason', 'refund_method', 'return_date')
    search_fields = ('return_number', 'sale__invoice_number', 'customer__first_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [ReturnItemInline]
    date_hierarchy = 'return_date'


@admin.register(ReturnItem)
class ReturnItemAdmin(admin.ModelAdmin):
    list_display = ('return_request', 'product', 'quantity', 'condition', 'subtotal')
    list_filter = ('condition',)
    search_fields = ('product__name', 'return_request__return_number')
    readonly_fields = ('id', 'created_at')


# ============================================
# SHIFTS & CASH MANAGEMENT
# ============================================

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('shift_number', 'user', 'branch', 'opening_time', 'closing_time', 'total_sales', 'cash_difference', 'is_closed')
    list_filter = ('is_closed', 'branch', 'opening_time')
    search_fields = ('shift_number', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'opening_time'


# ============================================
# M-PESA
# ============================================

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('merchant_request_id', 'phone_number', 'amount', 'status', 'mpesa_receipt_number', 'created_at')
    list_filter = ('status', 'transaction_type', 'created_at')
    search_fields = ('merchant_request_id', 'checkout_request_id', 'mpesa_receipt_number', 'phone_number')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


# ============================================
# PRODUCT BATCHES
# ============================================

@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'product', 'branch', 'quantity', 'expiry_date', 'is_expired')
    list_filter = ('is_expired', 'branch', 'expiry_date')
    search_fields = ('batch_number', 'product__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'expiry_date'


# Customize admin site headers
admin.site.site_header = "ERP System Administration"
admin.site.site_title = "ERP System Admin"
admin.site.index_title = "Welcome to ERP System Administration"