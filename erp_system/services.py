"""
Business logic layer for the ERP system.

Views stay thin and call into these services, so the same rules apply whether an
action comes from the API, the admin, a management command or a Celery task.

NOTE: model field names follow the README module list (see serializers.py). If your
models.py differs, adjust the attribute names used here.
"""
import base64
import logging
import re
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    Batch,
    Customer,
    MpesaTransaction,
    Notification,
    Payment,
    Promotion,
    PurchaseOrder,
    Sale,
    SaleItem,
    Shift,
    StockLevel,
    StockMovement,
)

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class ServiceError(Exception):
    """Raised for expected business-rule failures; views translate it to HTTP 400."""


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------
class StockService:
    @staticmethod
    @transaction.atomic
    def adjust(*, product, branch, quantity, movement_type, user=None, reference="", allow_negative=False):
        """Add (positive) or remove (negative) stock and record the movement."""
        quantity = Decimal(quantity)
        level, _ = StockLevel.objects.select_for_update().get_or_create(
            product=product, branch=branch, defaults={"quantity": ZERO}
        )
        new_quantity = level.quantity + quantity
        if new_quantity < 0 and not allow_negative:
            raise ServiceError(
                f"Insufficient stock for {product.name}: "
                f"{level.quantity} available, {abs(quantity)} requested."
            )
        level.quantity = new_quantity
        level.save(update_fields=["quantity"])

        StockMovement.objects.create(
            tenant=product.tenant,
            product=product,
            branch=branch,
            movement_type=movement_type,
            quantity=quantity,
            reference=reference,
            created_by=user,
        )
        StockService._maybe_alert_low_stock(product, branch, new_quantity)
        return level

    @staticmethod
    @transaction.atomic
    def transfer(*, product, from_branch, to_branch, quantity, user=None):
        reference = f"TRF-{uuid.uuid4().hex[:8].upper()}"
        StockService.adjust(
            product=product, branch=from_branch, quantity=-Decimal(quantity),
            movement_type="transfer", user=user, reference=reference,
        )
        StockService.adjust(
            product=product, branch=to_branch, quantity=Decimal(quantity),
            movement_type="transfer", user=user, reference=reference,
        )
        return reference

    @staticmethod
    def _maybe_alert_low_stock(product, branch, quantity):
        if quantity <= product.reorder_level:
            Notification.objects.create(
                tenant=product.tenant,
                notification_type="low_stock",
                title=f"Low stock: {product.name}",
                message=f"{product.name} is down to {quantity} at {branch.name}.",
            )

    @staticmethod
    def low_stock_queryset(tenant, branch=None):
        qs = StockLevel.objects.filter(
            product__tenant=tenant, quantity__lte=F("product__reorder_level")
        ).select_related("product", "branch")
        return qs.filter(branch=branch) if branch else qs

    @staticmethod
    def expiring_batches(tenant, days=None, branch=None):
        days = days or settings.EXPIRY_ALERT_DAYS
        cutoff = timezone.localdate() + timedelta(days=days)
        qs = Batch.objects.filter(
            product__tenant=tenant, quantity__gt=0, expiry_date__lte=cutoff
        ).select_related("product", "branch")
        return qs.filter(branch=branch) if branch else qs


# ---------------------------------------------------------------------------
# Purchasing
# ---------------------------------------------------------------------------
class PurchaseService:
    @staticmethod
    @transaction.atomic
    def approve(order, user):
        if order.status not in ("draft", "pending"):
            raise ServiceError(f"Cannot approve an order in '{order.status}' status.")
        order.status = "approved"
        order.approved_by = user
        order.save(update_fields=["status", "approved_by"])
        return order

    @staticmethod
    @transaction.atomic
    def receive(order, lines, user):
        """
        Receive goods against a purchase order.

        `lines` is a list of dicts: {item, quantity, batch_number, expiry_date}.
        Supports partial receiving; the order becomes 'received' once every item is complete.
        """
        if order.status not in ("approved", "ordered", "partially_received"):
            raise ServiceError(f"Cannot receive goods for an order in '{order.status}' status.")

        items = {item.id: item for item in order.items.select_for_update()}
        for line in lines:
            item = items.get(line["item"])
            if item is None:
                raise ServiceError(f"Item {line['item']} does not belong to this order.")
            quantity = Decimal(line["quantity"])
            outstanding = item.quantity - item.received_quantity
            if quantity > outstanding:
                raise ServiceError(
                    f"Cannot receive {quantity} of {item.product.name}; only {outstanding} outstanding."
                )

            item.received_quantity += quantity
            item.save(update_fields=["received_quantity"])

            StockService.adjust(
                product=item.product, branch=order.branch, quantity=quantity,
                movement_type="purchase", user=user, reference=order.order_number,
            )
            if line.get("batch_number") or line.get("expiry_date"):
                Batch.objects.create(
                    product=item.product, branch=order.branch,
                    batch_number=line.get("batch_number") or order.order_number,
                    expiry_date=line.get("expiry_date"), quantity=quantity,
                )

        fully_received = all(i.received_quantity >= i.quantity for i in items.values())
        order.status = "received" if fully_received else "partially_received"
        order.save(update_fields=["status"])
        return order


# ---------------------------------------------------------------------------
# Sales and POS
# ---------------------------------------------------------------------------
class SaleService:
    @staticmethod
    def _invoice_number(branch):
        stamp = timezone.localtime().strftime("%y%m%d")
        return f"INV-{branch.id}-{stamp}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _promotion_discount(tenant, code, subtotal):
        if not code:
            return ZERO, None
        today = timezone.localdate()
        promo = Promotion.objects.filter(
            tenant=tenant, code__iexact=code, is_active=True,
            start_date__lte=today, end_date__gte=today,
        ).first()
        if promo is None:
            raise ServiceError("Promotion code is invalid or has expired.")
        if promo.usage_limit and promo.times_used >= promo.usage_limit:
            raise ServiceError("This promotion has reached its usage limit.")
        if promo.discount_type == "percentage":
            discount = subtotal * promo.discount_value / Decimal("100")
        else:
            discount = promo.discount_value
        return money(min(discount, subtotal)), promo

    @staticmethod
    @transaction.atomic
    def checkout(*, user, data):
        """
        Create a sale from validated POS data.

        Deducts stock, applies promotions, records payments, awards loyalty points and
        updates the cashier's open shift. All in one transaction: if anything fails,
        nothing is saved.
        """
        branch = data["branch"]
        if branch.tenant_id != user.tenant_id and not user.is_superuser:
            raise ServiceError("You cannot sell from a branch outside your business.")

        tenant = branch.tenant
        customer = data.get("customer")
        if customer and customer.tenant_id != tenant.id:
            raise ServiceError("Customer belongs to a different business.")

        subtotal = tax_total = line_discounts = ZERO
        prepared = []
        for line in data["items"]:
            product = line["product"]
            if product.tenant_id != tenant.id:
                raise ServiceError(f"Product {product.name} belongs to a different business.")
            qty = Decimal(line["quantity"])
            unit_price = money(line.get("unit_price", product.selling_price))
            discount = money(line.get("discount_amount", ZERO))
            gross = money(qty * unit_price)
            net = gross - discount
            if net < 0:
                raise ServiceError(f"Discount on {product.name} exceeds the line total.")
            tax = money(net * (product.tax_rate or ZERO) / Decimal("100"))
            subtotal += net
            tax_total += tax
            line_discounts += discount
            prepared.append((product, qty, unit_price, discount, net))

        promo_discount, promo = SaleService._promotion_discount(
            tenant, data.get("promotion_code", ""), subtotal
        )
        extra_discount = money(data.get("discount_amount", ZERO))
        total_discount = promo_discount + extra_discount
        if total_discount > subtotal:
            raise ServiceError("Total discount exceeds the sale subtotal.")
        total = money(subtotal - total_discount + tax_total)

        payments = data.get("payments", [])
        paid = money(sum((Decimal(p["amount"]) for p in payments), ZERO))
        cash_paid = money(
            sum((Decimal(p["amount"]) for p in payments if p["method"] == "cash"), ZERO)
        )
        credit_paid = money(
            sum((Decimal(p["amount"]) for p in payments if p["method"] == "credit"), ZERO)
        )
        if credit_paid and not customer:
            raise ServiceError("A customer is required for credit sales.")
        if paid < total and not credit_paid:
            status = "pending"  # e.g. waiting for an M-Pesa confirmation
        else:
            status = "completed"
        if paid - cash_paid > total:
            raise ServiceError("Non-cash payments exceed the sale total.")

        sale = Sale.objects.create(
            tenant=tenant, branch=branch, customer=customer, cashier=user,
            invoice_number=SaleService._invoice_number(branch),
            subtotal=subtotal, discount_amount=total_discount + line_discounts,
            tax_amount=tax_total, total_amount=total, amount_paid=min(paid, total),
            status=status, notes=data.get("notes", ""),
        )

        for product, qty, unit_price, discount, net in prepared:
            SaleItem.objects.create(
                sale=sale, product=product, quantity=qty, unit_price=unit_price,
                discount_amount=discount, line_total=net,
            )
            StockService.adjust(
                product=product, branch=branch, quantity=-qty, movement_type="sale",
                user=user, reference=sale.invoice_number,
                allow_negative=getattr(getattr(tenant, "settings", None), "allow_negative_stock", False),
            )

        for p in payments:
            Payment.objects.create(
                tenant=tenant, sale=sale, method=p["method"], amount=p["amount"],
                reference=p.get("reference", ""),
                status="pending" if p["method"] == "mpesa" and status == "pending" else "completed",
            )

        if promo:
            Promotion.objects.filter(pk=promo.pk).update(times_used=F("times_used") + 1)

        if customer and status == "completed":
            points = int(total // Decimal(settings.LOYALTY_KES_PER_POINT))
            if points:
                Customer.objects.filter(pk=customer.pk).update(
                    loyalty_points=F("loyalty_points") + points
                )

        return sale

    @staticmethod
    @transaction.atomic
    def void(sale, user, reason=""):
        if sale.status == "cancelled":
            raise ServiceError("Sale is already cancelled.")
        for item in sale.items.select_related("product"):
            StockService.adjust(
                product=item.product, branch=sale.branch, quantity=item.quantity,
                movement_type="return", user=user, reference=f"VOID-{sale.invoice_number}",
            )
        sale.status = "cancelled"
        sale.notes = f"{sale.notes}\nVoided by {user.username}: {reason}".strip()
        sale.save(update_fields=["status", "notes"])
        return sale


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------
class ShiftService:
    @staticmethod
    @transaction.atomic
    def open(*, user, branch, opening_cash):
        if Shift.objects.filter(cashier=user, status="open").exists():
            raise ServiceError("You already have an open shift. Close it first.")
        return Shift.objects.create(
            tenant=user.tenant, branch=branch, cashier=user,
            opening_cash=opening_cash, status="open",
        )

    @staticmethod
    @transaction.atomic
    def close(shift, *, closing_cash, notes=""):
        if shift.status != "open":
            raise ServiceError("This shift is already closed.")
        cash_sales = Payment.objects.filter(
            sale__cashier=shift.cashier, sale__branch=shift.branch,
            sale__created_at__gte=shift.opened_at, method="cash", status="completed",
        ).aggregate(total=Coalesce(Sum("amount"), ZERO))["total"]
        shift.expected_cash = money(shift.opening_cash + cash_sales)
        shift.closing_cash = closing_cash
        shift.variance = money(Decimal(closing_cash) - shift.expected_cash)
        shift.closed_at = timezone.now()
        shift.status = "closed"
        shift.notes = notes
        shift.save()
        return shift


# ---------------------------------------------------------------------------
# M-Pesa (Safaricom Daraja)
# ---------------------------------------------------------------------------
class MpesaService:
    SANDBOX_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_URL = "https://api.safaricom.co.ke"
    TOKEN_CACHE_KEY = "mpesa_access_token"

    @property
    def base_url(self):
        return self.PRODUCTION_URL if settings.MPESA_ENVIRONMENT == "production" else self.SANDBOX_URL

    @staticmethod
    def normalize_phone(phone):
        """Convert 07xx / 01xx / +254 / 254 formats to 2547XXXXXXXX."""
        digits = re.sub(r"\D", "", phone or "")
        if digits.startswith("0") and len(digits) == 10:
            digits = "254" + digits[1:]
        elif len(digits) == 9 and digits[0] in "71":
            digits = "254" + digits
        if not re.fullmatch(r"254[17]\d{8}", digits):
            raise ServiceError("Enter a valid Safaricom number, e.g. 0712345678.")
        return digits

    def get_access_token(self):
        from django.core.cache import cache

        token = cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token
        if not (settings.MPESA_CONSUMER_KEY and settings.MPESA_CONSUMER_SECRET):
            raise ServiceError("M-Pesa credentials are not configured.")
        try:
            response = requests.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
                timeout=settings.MPESA_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("M-Pesa token request failed")
            raise ServiceError("Could not reach M-Pesa. Please try again.") from exc
        data = response.json()
        token = data["access_token"]
        cache.set(self.TOKEN_CACHE_KEY, token, int(data.get("expires_in", 3599)) - 60)
        return token

    @staticmethod
    def _password(timestamp):
        raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    def stk_push(self, *, tenant, phone_number, amount, sale=None,
                 account_reference="ERP", description="Payment"):
        if not settings.MPESA_CALLBACK_URL:
            raise ServiceError("MPESA_CALLBACK_URL is not configured.")
        phone = self.normalize_phone(phone_number)
        timestamp = timezone.now().astimezone(timezone.get_fixed_timezone(180)).strftime("%Y%m%d%H%M%S")
        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(Decimal(amount).to_integral_value(rounding=ROUND_HALF_UP)),
            "PartyA": phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": account_reference[:12],
            "TransactionDesc": description[:13],
        }
        try:
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {self.get_access_token()}"},
                timeout=settings.MPESA_REQUEST_TIMEOUT,
            )
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("M-Pesa STK push failed")
            raise ServiceError("M-Pesa request failed. Please try again.") from exc

        if response.status_code != 200 or body.get("ResponseCode") != "0":
            raise ServiceError(body.get("errorMessage") or body.get("ResponseDescription") or "STK push rejected.")

        return MpesaTransaction.objects.create(
            tenant=tenant, sale=sale, phone_number=phone, amount=amount,
            merchant_request_id=body["MerchantRequestID"],
            checkout_request_id=body["CheckoutRequestID"],
            status="pending", raw_response=body,
        )

    @staticmethod
    @transaction.atomic
    def handle_callback(payload):
        """Process the STK callback Safaricom posts to MPESA_CALLBACK_URL."""
        try:
            callback = payload["Body"]["stkCallback"]
            checkout_id = callback["CheckoutRequestID"]
            result_code = int(callback["ResultCode"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Malformed M-Pesa callback: %s", payload)
            return None

        txn = (
            MpesaTransaction.objects.select_for_update()
            .filter(checkout_request_id=checkout_id).first()
        )
        if txn is None:
            logger.warning("M-Pesa callback for unknown CheckoutRequestID %s", checkout_id)
            return None
        if txn.status != "pending":
            return txn  # Safaricom may retry; stay idempotent.

        txn.result_code = result_code
        txn.result_desc = callback.get("ResultDesc", "")
        txn.raw_response = payload

        if result_code == 0:
            items = {i["Name"]: i.get("Value") for i in callback["CallbackMetadata"]["Item"]}
            txn.status = "success"
            txn.mpesa_receipt_number = items.get("MpesaReceiptNumber", "")
            txn.save()
            MpesaService._confirm_sale_payment(txn)
        else:
            txn.status = "cancelled" if result_code == 1032 else "failed"
            txn.save()
        return txn

    @staticmethod
    def _confirm_sale_payment(txn):
        sale = txn.sale
        if sale is None:
            return
        Payment.objects.filter(sale=sale, method="mpesa", status="pending").update(
            status="completed", reference=txn.mpesa_receipt_number
        )
        paid = Payment.objects.filter(sale=sale, status="completed").aggregate(
            total=Coalesce(Sum("amount"), ZERO)
        )["total"]
        sale.amount_paid = min(paid, sale.total_amount)
        if paid >= sale.total_amount:
            sale.status = "completed"
        sale.save(update_fields=["amount_paid", "status"])
        Notification.objects.create(
            tenant=sale.tenant, notification_type="payment",
            title="M-Pesa payment received",
            message=f"{txn.mpesa_receipt_number}: KES {txn.amount} for {sale.invoice_number}.",
        )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class ReportService:
    @staticmethod
    def _sales(tenant, branch=None):
        qs = Sale.objects.filter(tenant=tenant, status="completed")
        return qs.filter(branch=branch) if branch else qs

    @staticmethod
    def daily_summary(tenant, date=None, branch=None):
        date = date or timezone.localdate()
        sales = ReportService._sales(tenant, branch).filter(created_at__date=date)
        totals = sales.aggregate(
            revenue=Coalesce(Sum("total_amount"), ZERO),
            tax=Coalesce(Sum("tax_amount"), ZERO),
            discounts=Coalesce(Sum("discount_amount"), ZERO),
        )
        by_method = (
            Payment.objects.filter(sale__in=sales, status="completed")
            .values("method").annotate(total=Sum("amount")).order_by("-total")
        )
        return {
            "date": date, "transactions": sales.count(), **totals,
            "payment_methods": list(by_method),
        }

    @staticmethod
    def sales_trend(tenant, days=7, branch=None):
        start = timezone.localdate() - timedelta(days=days - 1)
        rows = (
            ReportService._sales(tenant, branch).filter(created_at__date__gte=start)
            .values("created_at__date").annotate(total=Sum("total_amount"))
            .order_by("created_at__date")
        )
        lookup = {r["created_at__date"]: r["total"] for r in rows}
        return [
            {"date": start + timedelta(days=i), "total": lookup.get(start + timedelta(days=i), ZERO)}
            for i in range(days)
        ]

    @staticmethod
    def top_products(tenant, start, end, branch=None, limit=10):
        qs = SaleItem.objects.filter(
            sale__tenant=tenant, sale__status="completed",
            sale__created_at__date__range=(start, end),
        )
        if branch:
            qs = qs.filter(sale__branch=branch)
        return list(
            qs.values("product__id", "product__name")
            .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
            .order_by("-revenue")[:limit]
        )

    @staticmethod
    def sales_by_category(tenant, start, end, branch=None):
        qs = SaleItem.objects.filter(
            sale__tenant=tenant, sale__status="completed",
            sale__created_at__date__range=(start, end),
        )
        if branch:
            qs = qs.filter(sale__branch=branch)
        return list(
            qs.values("product__category__name")
            .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
            .order_by("-revenue")
        )

    @staticmethod
    def profit_and_loss(tenant, start, end, branch=None):
        from .models import Expense

        items = SaleItem.objects.filter(
            sale__tenant=tenant, sale__status="completed",
            sale__created_at__date__range=(start, end),
        )
        expenses = Expense.objects.filter(tenant=tenant, date__range=(start, end))
        if branch:
            items = items.filter(sale__branch=branch)
            expenses = expenses.filter(branch=branch)

        cost_expr = ExpressionWrapper(
            F("quantity") * F("product__cost_price"),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
        revenue = items.aggregate(v=Coalesce(Sum("line_total"), ZERO))["v"]
        cogs = items.aggregate(v=Coalesce(Sum(cost_expr), ZERO))["v"]
        expense_total = expenses.aggregate(v=Coalesce(Sum("amount"), ZERO))["v"]
        gross = revenue - cogs
        return {
            "start": start, "end": end, "revenue": revenue, "cost_of_goods_sold": cogs,
            "gross_profit": gross, "expenses": expense_total, "net_profit": gross - expense_total,
            "gross_margin_pct": money(gross / revenue * 100) if revenue else ZERO,
        }

    @staticmethod
    def inventory_valuation(tenant, branch=None):
        qs = StockLevel.objects.filter(product__tenant=tenant)
        if branch:
            qs = qs.filter(branch=branch)
        value_expr = ExpressionWrapper(
            F("quantity") * F("product__cost_price"),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        )
        agg = qs.aggregate(cost_value=Coalesce(Sum(value_expr), ZERO), units=Coalesce(Sum("quantity"), ZERO))
        return {"cost_value": agg["cost_value"], "units": agg["units"]}

    @staticmethod
    def top_customers(tenant, limit=10):
        return list(
            Sale.objects.filter(tenant=tenant, status="completed", customer__isnull=False)
            .values("customer__id", "customer__name")
            .annotate(total_spent=Sum("total_amount"), orders=Count("id"))
            .order_by("-total_spent")[:limit]
        )