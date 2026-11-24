"""
DRF serializers for the ERP system.

NOTE: field names below follow the module list in the README. If your models.py
uses different names, adjust the `fields` / `read_only_fields` entries to match.
"""
from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from .models import (
    AuditLog,
    Branch,
    Category,
    Customer,
    Employee,
    Expense,
    MpesaTransaction,
    Notification,
    Payment,
    Product,
    Promotion,
    PurchaseOrder,
    PurchaseOrderItem,
    Sale,
    SaleItem,
    SaleReturn,
    Shift,
    StockLevel,
    StockMovement,
    Supplier,
    Tenant,
    TenantSettings,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth and users
# ---------------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    full_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "phone", "user_type", "tenant", "branch", "branch_name", "is_active", "password",
        ]
        read_only_fields = ["id", "tenant", "full_name", "branch_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class EmployeeSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source="user", read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["tenant"]


# ---------------------------------------------------------------------------
# Tenancy
# ---------------------------------------------------------------------------
class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = "__all__"


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = "__all__"
        read_only_fields = ["tenant"]
        extra_kwargs = {
            "mpesa_consumer_secret": {"write_only": True},
            "mpesa_passkey": {"write_only": True},
        }


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ["tenant"]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ["tenant"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["tenant"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    total_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["tenant"]

    def get_total_stock(self, obj):
        # Use the annotated value when the view provides it, avoiding N+1 queries.
        if hasattr(obj, "total_stock_annotated"):
            return obj.total_stock_annotated or 0
        return sum(level.quantity for level in obj.stock_levels.all())


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    is_low = serializers.SerializerMethodField()

    class Meta:
        model = StockLevel
        fields = "__all__"

    def get_is_low(self, obj):
        return obj.quantity <= obj.product.reorder_level


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ["tenant", "created_by", "created_at"]


class StockAdjustmentSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Positive adds stock, negative removes stock.",
    )
    movement_type = serializers.ChoiceField(
        choices=["adjustment", "damage", "expiry", "return", "purchase"], default="adjustment"
    )
    reference = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity cannot be zero.")
        return value


class StockTransferSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    from_branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    to_branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    def validate(self, attrs):
        if attrs["from_branch"] == attrs["to_branch"]:
            raise serializers.ValidationError("Source and destination branches must differ.")
        return attrs


# ---------------------------------------------------------------------------
# Purchasing
# ---------------------------------------------------------------------------
class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id", "product", "product_name", "quantity", "unit_cost", "received_quantity",
        ]
        read_only_fields = ["id", "received_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ["tenant", "status", "created_by", "approved_by", "order_number"]

    def get_total_amount(self, obj):
        return sum(i.quantity * i.unit_cost for i in obj.items.all())

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A purchase order needs at least one item.")
        return value

    def create(self, validated_data):
        items = validated_data.pop("items")
        order = PurchaseOrder.objects.create(**validated_data)
        PurchaseOrderItem.objects.bulk_create(
            [PurchaseOrderItem(purchase_order=order, **item) for item in items]
        )
        return order

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            PurchaseOrderItem.objects.bulk_create(
                [PurchaseOrderItem(purchase_order=instance, **item) for item in items]
            )
        return instance


class ReceiveItemSerializer(serializers.Serializer):
    item = serializers.IntegerField(help_text="PurchaseOrderItem id")
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    batch_number = serializers.CharField(required=False, allow_blank=True, default="")
    expiry_date = serializers.DateField(required=False, allow_null=True, default=None)


class ReceivePurchaseOrderSerializer(serializers.Serializer):
    items = ReceiveItemSerializer(many=True)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["tenant", "loyalty_points"]


# ---------------------------------------------------------------------------
# Sales and payments
# ---------------------------------------------------------------------------
class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = SaleItem
        fields = [
            "id", "product", "product_name", "quantity", "unit_price",
            "discount_amount", "line_total",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["tenant", "created_at"]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default=None)
    cashier_name = serializers.CharField(source="cashier.username", read_only=True)

    class Meta:
        model = Sale
        fields = "__all__"
        read_only_fields = fields


class CheckoutItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0"), min_value=Decimal("0")
    )


class CheckoutPaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField(
        choices=["cash", "mpesa", "card", "bank_transfer", "credit", "cheque"]
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(required=False, allow_blank=True, default="")


class CheckoutSerializer(serializers.Serializer):
    """Payload sent by the POS screen to create a sale in one request."""

    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())
    customer = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), required=False, allow_null=True
    )
    items = CheckoutItemSerializer(many=True)
    payments = CheckoutPaymentSerializer(many=True, required=False)
    discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0"), min_value=Decimal("0")
    )
    promotion_code = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("The cart is empty.")
        return value


class StkPushSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("1"))
    sale = serializers.PrimaryKeyRelatedField(
        queryset=Sale.objects.all(), required=False, allow_null=True
    )
    account_reference = serializers.CharField(required=False, default="ERP", max_length=12)
    description = serializers.CharField(required=False, default="Payment", max_length=13)


class MpesaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MpesaTransaction
        exclude = ["raw_response"]
        read_only_fields = ["tenant"]


# ---------------------------------------------------------------------------
# Returns, expenses, shifts, promotions
# ---------------------------------------------------------------------------
class SaleReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleReturn
        fields = "__all__"
        read_only_fields = ["tenant", "status", "processed_by", "approved_by"]


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"
        read_only_fields = ["tenant", "created_by"]


class ShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(source="cashier.username", read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"
        read_only_fields = [
            "tenant", "cashier", "opened_at", "closed_at", "expected_cash", "variance", "status",
        ]


class ShiftCloseSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"
        read_only_fields = ["tenant", "times_used"]

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError("End date cannot be before start date.")
        return attrs


# ---------------------------------------------------------------------------
# Notifications and audit
# ---------------------------------------------------------------------------
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ["tenant", "user", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = fields