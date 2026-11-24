"""
API views. Business rules live in services.py; views handle HTTP, permissions and tenancy.
"""
import logging
from datetime import date, timedelta

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AuditLog, Branch, Category, Customer, Employee, Expense, MpesaTransaction,
    Notification, Payment, Product, Promotion, PurchaseOrder, Sale, SaleReturn,
    Shift, StockLevel, StockMovement, Supplier, TenantSettings,
)
from .serializers import (
    AuditLogSerializer, BranchSerializer, CategorySerializer, CheckoutSerializer,
    CustomerSerializer, EmployeeSerializer, ExpenseSerializer, LoginSerializer,
    MpesaTransactionSerializer, NotificationSerializer, PaymentSerializer,
    ProductSerializer, PromotionSerializer, PurchaseOrderSerializer,
    ReceivePurchaseOrderSerializer, SaleReturnSerializer, SaleSerializer,
    ShiftCloseSerializer, ShiftSerializer, StkPushSerializer,
    StockAdjustmentSerializer, StockLevelSerializer, StockMovementSerializer,
    StockTransferSerializer, SupplierSerializer, TenantSettingsSerializer,
    UserSerializer,
)
from .services import (
    MpesaService, PurchaseService, ReportService, SaleService, ServiceError,
    ShiftService, StockService,
)

logger = logging.getLogger(__name__)

ADMIN_ROLES = {"super_admin", "tenant_admin"}
MANAGER_ROLES = ADMIN_ROLES | {"branch_manager"}


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
class RolePermission(permissions.BasePermission):
    """
    Views set `write_roles`; any authenticated user can read, only those roles can write.
    Leave `write_roles` as None to allow every authenticated user to write.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS or request.user.is_superuser:
            return True
        roles = getattr(view, "write_roles", None)
        return roles is None or request.user.user_type in roles


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------
class TenantScopedViewSet(viewsets.ModelViewSet):
    """
    Restricts every query to the caller's tenant and stamps new rows with it.
    Branch-level staff are additionally limited to their own branch when the model
    has a `branch` field and `branch_scoped = True`.
    """

    permission_classes = [RolePermission]
    tenant_field = "tenant"
    branch_scoped = False
    write_roles = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(**{self.tenant_field: user.tenant})
        if self.branch_scoped and user.user_type not in ADMIN_ROLES and user.branch_id:
            qs = qs.filter(branch=user.branch)
        return qs

    def perform_create(self, serializer):
        extra = {}
        if self.tenant_field == "tenant":
            extra["tenant"] = self.request.user.tenant
        if "created_by" in serializer.Meta.model._meta.fields_map or hasattr(
            serializer.Meta.model, "created_by"
        ):
            extra["created_by"] = self.request.user
        serializer.save(**extra)


def service_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def parse_range(request, default_days=30):
    today = timezone.localdate()
    try:
        end = date.fromisoformat(request.query_params.get("end", ""))
    except ValueError:
        end = today
    try:
        start = date.fromisoformat(request.query_params.get("start", ""))
    except ValueError:
        start = end - timedelta(days=default_days - 1)
    return start, end


def report_branch(request):
    branch_id = request.query_params.get("branch")
    user = request.user
    if user.user_type not in ADMIN_ROLES and user.branch_id:
        return user.branch  # branch staff only see their branch
    return Branch.objects.filter(pk=branch_id, tenant=user.tenant).first() if branch_id else None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        AuditLog.objects.create(
            tenant=user.tenant, user=user, action="login",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Organisation
# ---------------------------------------------------------------------------
class BranchViewSet(TenantScopedViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    write_roles = ADMIN_ROLES
    search_fields = ["name", "code", "address"]


class UserViewSet(TenantScopedViewSet):
    queryset = UserSerializer.Meta.model.objects.all()
    serializer_class = UserSerializer
    write_roles = ADMIN_ROLES
    search_fields = ["username", "first_name", "last_name", "email"]
    filterset_fields = ["user_type", "branch", "is_active"]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class EmployeeViewSet(TenantScopedViewSet):
    queryset = Employee.objects.select_related("user")
    serializer_class = EmployeeSerializer
    write_roles = ADMIN_ROLES


class TenantSettingsView(APIView):
    """GET/PUT the current tenant's settings (one row per tenant)."""

    def _get(self, request):
        obj, _ = TenantSettings.objects.get_or_create(tenant=request.user.tenant)
        return obj

    def get(self, request):
        return Response(TenantSettingsSerializer(self._get(request)).data)

    def put(self, request):
        if request.user.user_type not in ADMIN_ROLES and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = TenantSettingsSerializer(self._get(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
INVENTORY_WRITERS = MANAGER_ROLES | {"inventory_manager"}


class CategoryViewSet(TenantScopedViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    write_roles = INVENTORY_WRITERS
    search_fields = ["name"]


class SupplierViewSet(TenantScopedViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    write_roles = INVENTORY_WRITERS
    search_fields = ["name", "phone", "email"]


class ProductViewSet(TenantScopedViewSet):
    queryset = Product.objects.select_related("category").prefetch_related("stock_levels")
    serializer_class = ProductSerializer
    write_roles = INVENTORY_WRITERS
    search_fields = ["name", "sku", "barcode"]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["name", "selling_price", "created_at"]

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        """Exact barcode / SKU lookup used by the POS scanner."""
        code = request.query_params.get("code", "").strip()
        product = self.get_queryset().filter(is_active=True).filter(
            barcode=code
        ).first() or self.get_queryset().filter(is_active=True, sku__iexact=code).first()
        if product is None:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(product).data)


class StockLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockLevel.objects.select_related("product", "branch")
    serializer_class = StockLevelSerializer
    filterset_fields = ["branch", "product"]
    search_fields = ["product__name", "product__sku"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(product__tenant=user.tenant)
        if user.user_type not in ADMIN_ROLES and user.branch_id:
            qs = qs.filter(branch=user.branch)
        return qs

    @action(detail=False, methods=["get"])
    def low(self, request):
        branch = report_branch(request)
        qs = StockService.low_stock_queryset(request.user.tenant, branch)
        return Response(self.get_serializer(qs, many=True).data)


class StockMovementViewSet(TenantScopedViewSet):
    queryset = StockMovement.objects.select_related("product", "branch")
    serializer_class = StockMovementSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["branch", "product", "movement_type"]
    branch_scoped = True


class StockActionsViewSet(viewsets.ViewSet):
    """Stock adjustments and transfers (always go through StockService)."""

    permission_classes = [RolePermission]
    write_roles = INVENTORY_WRITERS

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            level = StockService.adjust(user=request.user, **data)
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(StockLevelSerializer(level).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        serializer = StockTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ref = StockService.transfer(user=request.user, **serializer.validated_data)
        except ServiceError as exc:
            return service_error_response(exc)
        return Response({"reference": ref}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        batches = StockService.expiring_batches(request.user.tenant, branch=report_branch(request))
        return Response([
            {
                "id": b.id, "product": b.product.name, "branch": b.branch.name,
                "batch_number": b.batch_number, "expiry_date": b.expiry_date,
                "quantity": b.quantity,
            }
            for b in batches
        ])


# ---------------------------------------------------------------------------
# Purchasing
# ---------------------------------------------------------------------------
class PurchaseOrderViewSet(TenantScopedViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier", "branch").prefetch_related(
        "items__product"
    )
    serializer_class = PurchaseOrderSerializer
    write_roles = INVENTORY_WRITERS
    filterset_fields = ["status", "supplier", "branch"]
    search_fields = ["order_number", "supplier__name"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.user_type not in MANAGER_ROLES and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            order = PurchaseService.approve(self.get_object(), request.user)
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        serializer = ReceivePurchaseOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = PurchaseService.receive(
                self.get_object(), serializer.validated_data["items"], request.user
            )
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status in ("received", "completed"):
            return Response({"detail": "Received orders cannot be cancelled."}, status=400)
        order.status = "cancelled"
        order.save(update_fields=["status"])
        return Response(self.get_serializer(order).data)


# ---------------------------------------------------------------------------
# Customers, sales and POS
# ---------------------------------------------------------------------------
class CustomerViewSet(TenantScopedViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ["name", "phone", "email"]
    filterset_fields = ["customer_type"]


class SaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sale.objects.select_related("customer", "cashier", "branch").prefetch_related(
        "items__product", "payments"
    )
    serializer_class = SaleSerializer
    filterset_fields = ["branch", "status", "customer", "cashier"]
    search_fields = ["invoice_number", "customer__name"]
    ordering_fields = ["created_at", "total_amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(tenant=user.tenant)
        if user.user_type not in MANAGER_ROLES and user.user_type != "accountant":
            qs = qs.filter(cashier=user)
        elif user.user_type == "branch_manager" and user.branch_id:
            qs = qs.filter(branch=user.branch)
        return qs

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sale = SaleService.checkout(user=request.user, data=serializer.validated_data)
        except ServiceError as exc:
            return service_error_response(exc)
        sale = self.get_queryset().get(pk=sale.pk)
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        if request.user.user_type not in MANAGER_ROLES and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            sale = SaleService.void(self.get_object(), request.user, request.data.get("reason", ""))
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(self.get_serializer(sale).data)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related("sale")
    serializer_class = PaymentSerializer
    filterset_fields = ["method", "status", "sale"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.is_superuser else qs.filter(tenant=self.request.user.tenant)


class SaleReturnViewSet(TenantScopedViewSet):
    queryset = SaleReturn.objects.select_related("sale")
    serializer_class = SaleReturnSerializer
    filterset_fields = ["status", "reason"]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant, processed_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.user_type not in MANAGER_ROLES and not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.status != "pending":
            return Response({"detail": "Only pending returns can be approved."}, status=400)
        obj.status = "approved"
        obj.approved_by = request.user
        obj.save(update_fields=["status", "approved_by"])
        return Response(self.get_serializer(obj).data)


# ---------------------------------------------------------------------------
# Expenses, shifts, promotions
# ---------------------------------------------------------------------------
class ExpenseViewSet(TenantScopedViewSet):
    queryset = Expense.objects.select_related("branch")
    serializer_class = ExpenseSerializer
    write_roles = MANAGER_ROLES | {"accountant"}
    filterset_fields = ["branch", "category", "payment_method"]
    search_fields = ["description"]
    branch_scoped = True


class ShiftViewSet(TenantScopedViewSet):
    queryset = Shift.objects.select_related("cashier", "branch")
    serializer_class = ShiftSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["branch", "cashier", "status"]
    branch_scoped = True

    def create(self, request, *args, **kwargs):
        """Open a shift."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = ShiftService.open(
                user=request.user,
                branch=serializer.validated_data["branch"],
                opening_cash=serializer.validated_data["opening_cash"],
            )
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(self.get_serializer(shift).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def current(self, request):
        shift = self.get_queryset().filter(cashier=request.user, status="open").first()
        return Response(self.get_serializer(shift).data if shift else None)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        serializer = ShiftCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = ShiftService.close(self.get_object(), **serializer.validated_data)
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(self.get_serializer(shift).data)


class PromotionViewSet(TenantScopedViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    write_roles = MANAGER_ROLES
    filterset_fields = ["is_active", "discount_type"]
    search_fields = ["name", "code"]


# ---------------------------------------------------------------------------
# Notifications and audit
# ---------------------------------------------------------------------------
class NotificationViewSet(TenantScopedViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["is_read", "notification_type"]

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        obj = self.get_object()
        obj.is_read = True
        obj.save(update_fields=["is_read"])
        return Response(self.get_serializer(obj).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    filterset_fields = ["user", "action"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        if user.user_type not in ADMIN_ROLES:
            return qs.none()
        return qs.filter(tenant=user.tenant)


# ---------------------------------------------------------------------------
# M-Pesa
# ---------------------------------------------------------------------------
class StkPushView(APIView):
    def post(self, request):
        serializer = StkPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sale = data.get("sale")
        if sale and sale.tenant_id != request.user.tenant_id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            txn = MpesaService().stk_push(
                tenant=request.user.tenant, phone_number=data["phone_number"],
                amount=data["amount"], sale=sale,
                account_reference=data["account_reference"], description=data["description"],
            )
        except ServiceError as exc:
            return service_error_response(exc)
        return Response(MpesaTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class MpesaStatusView(APIView):
    """Polled by the POS to see whether the customer approved the prompt."""

    def get(self, request, checkout_request_id):
        txn = MpesaTransaction.objects.filter(
            checkout_request_id=checkout_request_id, tenant=request.user.tenant
        ).first()
        if txn is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(MpesaTransactionSerializer(txn).data)


class MpesaCallbackView(APIView):
    """Public endpoint called by Safaricom. Always answers 200 so it does not retry."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def post(self, request):
        try:
            MpesaService.handle_callback(request.data)
        except Exception:  # noqa: BLE001 - never let Safaricom see a 500
            logger.exception("Error processing M-Pesa callback")
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MpesaTransaction.objects.all()
    serializer_class = MpesaTransactionSerializer
    filterset_fields = ["status"]
    search_fields = ["phone_number", "mpesa_receipt_number"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.is_superuser else qs.filter(tenant=self.request.user.tenant)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class ReportViewSet(viewsets.ViewSet):
    """Read-only analytics. Branch staff only see their own branch."""

    def _check(self, request):
        return request.user.user_type in MANAGER_ROLES | {"accountant", "inventory_manager"} \
            or request.user.is_superuser

    def list(self, request):
        return Response({"reports": [
            "dashboard", "daily-sales", "sales-trend", "top-products", "sales-by-category",
            "profit-loss", "inventory-valuation", "top-customers",
        ]})

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        tenant, branch = request.user.tenant, report_branch(request)
        low = StockService.low_stock_queryset(tenant, branch).count()
        expiring = StockService.expiring_batches(tenant, branch=branch).count()
        return Response({
            "today": ReportService.daily_summary(tenant, branch=branch),
            "trend": ReportService.sales_trend(tenant, 7, branch),
            "low_stock_count": low,
            "expiring_count": expiring,
            "unread_notifications": Notification.objects.filter(tenant=tenant, is_read=False).count(),
        })

    @action(detail=False, methods=["get"], url_path="daily-sales")
    def daily_sales(self, request):
        try:
            day = date.fromisoformat(request.query_params.get("date", ""))
        except ValueError:
            day = None
        return Response(ReportService.daily_summary(request.user.tenant, day, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="sales-trend")
    def sales_trend(self, request):
        days = min(int(request.query_params.get("days", 14)), 90)
        return Response(ReportService.sales_trend(request.user.tenant, days, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="top-products")
    def top_products(self, request):
        start, end = parse_range(request)
        return Response(ReportService.top_products(request.user.tenant, start, end, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="sales-by-category")
    def sales_by_category(self, request):
        start, end = parse_range(request)
        return Response(ReportService.sales_by_category(request.user.tenant, start, end, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="profit-loss")
    def profit_loss(self, request):
        if not self._check(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        start, end = parse_range(request)
        return Response(ReportService.profit_and_loss(request.user.tenant, start, end, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="inventory-valuation")
    def inventory_valuation(self, request):
        if not self._check(request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(ReportService.inventory_valuation(request.user.tenant, report_branch(request)))

    @action(detail=False, methods=["get"], url_path="top-customers")
    def top_customers(self, request):
        return Response(ReportService.top_customers(request.user.tenant))