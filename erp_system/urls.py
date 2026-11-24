"""API routes for the ERP app. Mounted at /api/ by config/urls.py."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("branches", views.BranchViewSet, basename="branch")
router.register("users", views.UserViewSet, basename="user")
router.register("employees", views.EmployeeViewSet, basename="employee")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("suppliers", views.SupplierViewSet, basename="supplier")
router.register("products", views.ProductViewSet, basename="product")
router.register("stock-levels", views.StockLevelViewSet, basename="stock-level")
router.register("stock-movements", views.StockMovementViewSet, basename="stock-movement")
router.register("stock", views.StockActionsViewSet, basename="stock")
router.register("purchase-orders", views.PurchaseOrderViewSet, basename="purchase-order")
router.register("customers", views.CustomerViewSet, basename="customer")
router.register("sales", views.SaleViewSet, basename="sale")
router.register("payments", views.PaymentViewSet, basename="payment")
router.register("returns", views.SaleReturnViewSet, basename="return")
router.register("expenses", views.ExpenseViewSet, basename="expense")
router.register("shifts", views.ShiftViewSet, basename="shift")
router.register("promotions", views.PromotionViewSet, basename="promotion")
router.register("notifications", views.NotificationViewSet, basename="notification")
router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")
router.register("mpesa/transactions", views.MpesaTransactionViewSet, basename="mpesa-transaction")
router.register("reports", views.ReportViewSet, basename="report")

urlpatterns = [
    # Authentication
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    # Tenant settings (single object per tenant)
    path("settings/", views.TenantSettingsView.as_view(), name="tenant-settings"),
    # M-Pesa
    path("mpesa/stk-push/", views.StkPushView.as_view(), name="mpesa-stk-push"),
    path("mpesa/status/<str:checkout_request_id>/", views.MpesaStatusView.as_view(), name="mpesa-status"),
    path("mpesa/callback/", views.MpesaCallbackView.as_view(), name="mpesa-callback"),
    # Everything else
    path("", include(router.urls)),
]