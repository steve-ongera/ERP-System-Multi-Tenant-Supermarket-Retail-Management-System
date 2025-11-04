from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from decimal import Decimal
import json
import uuid
from datetime import datetime

from .models import (
    Product, Stock, Sale, SaleItem, Payment, Customer,
    Branch, Category, MpesaTransaction, Shift, StockMovement
)


@login_required
def pos_view(request):
    """Main POS interface"""
    user = request.user
    
    # Ensure user has access to POS
    if user.user_type not in ['super_admin', 'tenant_admin', 'branch_manager', 'cashier']:
        return redirect('dashboard')
    
    # Get user's branch
    branch = user.branch if user.branch else user.tenant.branches.filter(is_main_branch=True).first()
    
    if not branch:
        return redirect('dashboard')
    
    # Get categories for filtering
    categories = Category.objects.filter(
        tenant=user.tenant,
        is_active=True
    ).order_by('name')
    
    # Get active shift for current user
    active_shift = Shift.objects.filter(
        user=user,
        branch=branch,
        is_closed=False
    ).first()
    
    context = {
        'branch': branch,
        'categories': categories,
        'active_shift': active_shift,
        'tenant': user.tenant,
    }
    
    return render(request, 'pos/pos.html', context)


@login_required
@require_http_methods(["GET"])
def search_products(request):
    """Search products with autocomplete"""
    query = request.GET.get('q', '').strip()
    branch_id = request.GET.get('branch_id')
    category_id = request.GET.get('category_id')
    
    if not query or len(query) < 2:
        return JsonResponse({'products': []})
    
    user = request.user
    branch = get_object_or_404(Branch, id=branch_id, tenant=user.tenant)
    
    # Search products
    products = Product.objects.filter(
        tenant=user.tenant,
        is_active=True
    ).filter(
        Q(name__icontains=query) |
        Q(sku__icontains=query) |
        Q(barcode__icontains=query)
    )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Get stock information
    products = products.select_related('category').prefetch_related('stocks')
    
    products_data = []
    for product in products[:20]:  # Limit to 20 results
        try:
            stock = product.stocks.get(branch=branch)
            available_qty = stock.available_quantity
        except Stock.DoesNotExist:
            available_qty = 0
        
        products_data.append({
            'id': str(product.id),
            'name': product.name,
            'sku': product.sku,
            'barcode': product.barcode,
            'selling_price': float(product.selling_price),
            'final_price': float(product.final_price),
            'discount_percentage': float(product.discount_percentage),
            'tax_percentage': float(product.tax_percentage),
            'available_quantity': available_qty,
            'unit_of_measure': product.unit_of_measure,
            'image': product.image.url if product.image else None,
            'category': product.category.name if product.category else 'N/A'
        })
    
    return JsonResponse({'products': products_data})


@login_required
@require_http_methods(["GET"])
def get_product_by_barcode(request):
    """Get product details by barcode scan"""
    barcode = request.GET.get('barcode', '').strip()
    branch_id = request.GET.get('branch_id')
    
    if not barcode:
        return JsonResponse({'error': 'No barcode provided'}, status=400)
    
    user = request.user
    branch = get_object_or_404(Branch, id=branch_id, tenant=user.tenant)
    
    try:
        product = Product.objects.select_related('category').get(
            tenant=user.tenant,
            barcode=barcode,
            is_active=True
        )
        
        # Get stock
        try:
            stock = product.stocks.get(branch=branch)
            available_qty = stock.available_quantity
        except Stock.DoesNotExist:
            available_qty = 0
        
        product_data = {
            'id': str(product.id),
            'name': product.name,
            'sku': product.sku,
            'barcode': product.barcode,
            'selling_price': float(product.selling_price),
            'final_price': float(product.final_price),
            'discount_percentage': float(product.discount_percentage),
            'tax_percentage': float(product.tax_percentage),
            'available_quantity': available_qty,
            'unit_of_measure': product.unit_of_measure,
            'image': product.image.url if product.image else None,
            'category': product.category.name if product.category else 'N/A'
        }
        
        return JsonResponse({'success': True, 'product': product_data})
        
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_http_methods(["GET"])
def get_popular_products(request):
    """Get most bought products"""
    branch_id = request.GET.get('branch_id')
    limit = int(request.GET.get('limit', 12))
    
    user = request.user
    branch = get_object_or_404(Branch, id=branch_id, tenant=user.tenant)
    
    # Get popular products based on sales
    popular_products = Product.objects.filter(
        tenant=user.tenant,
        is_active=True,
        sale_items__sale__branch=branch
    ).annotate(
        total_sold=Sum('sale_items__quantity')
    ).order_by('-total_sold')[:limit]
    
    products_data = []
    for product in popular_products:
        try:
            stock = product.stocks.get(branch=branch)
            available_qty = stock.available_quantity
        except Stock.DoesNotExist:
            available_qty = 0
        
        products_data.append({
            'id': str(product.id),
            'name': product.name,
            'sku': product.sku,
            'selling_price': float(product.selling_price),
            'final_price': float(product.final_price),
            'discount_percentage': float(product.discount_percentage),
            'tax_percentage': float(product.tax_percentage),
            'available_quantity': available_qty,
            'unit_of_measure': product.unit_of_measure,
            'image': product.image.url if product.image else None,
        })
    
    return JsonResponse({'products': products_data})


@login_required
@require_http_methods(["GET"])
def search_customers(request):
    """Search customers with autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'customers': []})
    
    user = request.user
    
    customers = Customer.objects.filter(
        tenant=user.tenant,
        is_active=True
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query) |
        Q(customer_code__icontains=query)
    )[:10]
    
    customers_data = [{
        'id': str(c.id),
        'name': f"{c.first_name} {c.last_name}",
        'customer_code': c.customer_code,
        'phone': c.phone,
        'customer_type': c.customer_type,
        'loyalty_points': c.loyalty_points,
        'credit_limit': float(c.credit_limit),
        'current_balance': float(c.current_balance)
    } for c in customers]
    
    return JsonResponse({'customers': customers_data})


@login_required
@require_http_methods(["POST"])
def process_sale(request):
    """Process a sale transaction"""
    try:
        data = json.loads(request.body)
        user = request.user
        
        # Validate data
        items = data.get('items', [])
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method')
        amount_paid = Decimal(str(data.get('amount_paid', 0)))
        mpesa_phone = data.get('mpesa_phone')
        branch_id = data.get('branch_id')
        
        if not items:
            return JsonResponse({'error': 'No items in cart'}, status=400)
        
        if not payment_method:
            return JsonResponse({'error': 'Payment method required'}, status=400)
        
        branch = get_object_or_404(Branch, id=branch_id, tenant=user.tenant)
        
        # Get or create customer
        customer = None
        if customer_id:
            customer = get_object_or_404(Customer, id=customer_id, tenant=user.tenant)
        
        # Calculate totals
        subtotal = Decimal('0')
        tax_amount = Decimal('0')
        discount_amount = Decimal('0')
        
        for item in items:
            item_subtotal = Decimal(str(item['final_price'])) * Decimal(str(item['quantity']))
            item_discount = Decimal(str(item['selling_price'])) * Decimal(str(item['discount_percentage'])) / 100 * Decimal(str(item['quantity']))
            item_tax = item_subtotal * Decimal(str(item['tax_percentage'])) / 100
            
            subtotal += item_subtotal
            discount_amount += item_discount
            tax_amount += item_tax
        
        total_amount = subtotal + tax_amount
        change_given = amount_paid - total_amount if amount_paid >= total_amount else Decimal('0')
        
        # Generate invoice number
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create sale
        sale = Sale.objects.create(
            tenant=user.tenant,
            branch=branch,
            customer=customer,
            invoice_number=invoice_number,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            amount_paid=amount_paid,
            change_given=change_given,
            payment_status='paid' if amount_paid >= total_amount else 'partial',
            sale_type='pos',
            created_by=user
        )
        
        # Create sale items and update stock
        for item_data in items:
            product = get_object_or_404(Product, id=item_data['id'], tenant=user.tenant)
            
            # Create sale item
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=item_data['quantity'],
                unit_price=Decimal(str(item_data['selling_price'])),
                discount_percentage=Decimal(str(item_data['discount_percentage'])),
                tax_percentage=Decimal(str(item_data['tax_percentage'])),
                subtotal=Decimal(str(item_data['final_price'])) * Decimal(str(item_data['quantity']))
            )
            
            # Update stock
            stock = Stock.objects.get(product=product, branch=branch)
            stock.quantity -= item_data['quantity']
            stock.save()
            
            # Create stock movement
            StockMovement.objects.create(
                product=product,
                branch=branch,
                movement_type='sale',
                quantity=-item_data['quantity'],
                unit_cost=product.cost_price,
                reference_number=invoice_number,
                created_by=user
            )
        
        # Handle M-Pesa payment
        if payment_method == 'mpesa':
            # Create payment record
            payment = Payment.objects.create(
                tenant=user.tenant,
                sale=sale,
                customer=customer,
                transaction_id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
                payment_method='mpesa',
                amount=amount_paid,
                mpesa_phone_number=mpesa_phone,
                created_by=user
            )
            
            # Initiate M-Pesa STK Push
            # This will be handled by the frontend JavaScript
            return JsonResponse({
                'success': True,
                'sale_id': str(sale.id),
                'invoice_number': invoice_number,
                'payment_id': str(payment.id),
                'initiate_mpesa': True,
                'mpesa_phone': mpesa_phone,
                'amount': float(amount_paid)
            })
        else:
            # Create payment for other methods
            Payment.objects.create(
                tenant=user.tenant,
                sale=sale,
                customer=customer,
                transaction_id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
                payment_method=payment_method,
                amount=amount_paid,
                created_by=user
            )
            
            return JsonResponse({
                'success': True,
                'sale_id': str(sale.id),
                'invoice_number': invoice_number,
                'total_amount': float(total_amount),
                'change_given': float(change_given)
            })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def initiate_mpesa_payment(request):
    """Initiate M-Pesa STK Push"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        amount = data.get('amount')
        payment_id = data.get('payment_id')
        
        # Normalize phone number
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        # Get tenant settings
        user = request.user
        settings = user.tenant.settings
        
        if not settings.mpesa_enabled:
            return JsonResponse({'error': 'M-Pesa not enabled'}, status=400)
        
        # Here you would integrate with M-Pesa API
        # For now, create a transaction record
        merchant_request_id = f"MR-{uuid.uuid4().hex[:12].upper()}"
        checkout_request_id = f"CR-{uuid.uuid4().hex[:12].upper()}"
        
        mpesa_transaction = MpesaTransaction.objects.create(
            tenant=user.tenant,
            payment_id=payment_id,
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
            phone_number=phone_number,
            amount=Decimal(str(amount)),
            transaction_type='stk_push',
            status='pending'
        )
        
        # TODO: Implement actual M-Pesa STK Push API call
        # For now, return success
        
        return JsonResponse({
            'success': True,
            'merchant_request_id': merchant_request_id,
            'checkout_request_id': checkout_request_id,
            'message': 'STK Push initiated. Please check your phone.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def check_mpesa_status(request):
    """Check M-Pesa transaction status"""
    checkout_request_id = request.GET.get('checkout_request_id')
    
    if not checkout_request_id:
        return JsonResponse({'error': 'Checkout request ID required'}, status=400)
    
    try:
        transaction = MpesaTransaction.objects.get(
            checkout_request_id=checkout_request_id,
            tenant=request.user.tenant
        )
        
        return JsonResponse({
            'success': True,
            'status': transaction.status,
            'result_code': transaction.result_code,
            'result_description': transaction.result_description,
            'mpesa_receipt_number': transaction.mpesa_receipt_number
        })
        
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({'error': 'Transaction not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def mpesa_callback(request):
    """M-Pesa callback endpoint"""
    try:
        data = json.loads(request.body)
        
        # Extract M-Pesa callback data
        # This structure depends on your M-Pesa integration
        checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
        result_desc = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')
        
        if checkout_request_id:
            transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )
            
            if result_code == '0':
                # Success
                transaction.status = 'success'
                transaction.result_code = result_code
                transaction.result_description = result_desc
                
                # Extract receipt number
                callback_metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])
                for item in callback_metadata:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        transaction.mpesa_receipt_number = item.get('Value')
                        break
                
                transaction.callback_data = data
                transaction.transaction_date = timezone.now()
                transaction.save()
                
                # Update payment
                if transaction.payment:
                    transaction.payment.mpesa_receipt_number = transaction.mpesa_receipt_number
                    transaction.payment.save()
                    
                    # Update sale status
                    if transaction.payment.sale:
                        transaction.payment.sale.payment_status = 'paid'
                        transaction.payment.sale.save()
            else:
                # Failed
                transaction.status = 'failed'
                transaction.result_code = result_code
                transaction.result_description = result_desc
                transaction.callback_data = data
                transaction.save()
        
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
        
    except Exception as e:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})


@login_required
@require_http_methods(["POST"])
def start_shift(request):
    """Start a new cashier shift"""
    try:
        data = json.loads(request.body)
        opening_cash = Decimal(str(data.get('opening_cash', 0)))
        opening_notes = data.get('opening_notes', '')
        
        user = request.user
        branch = user.branch if user.branch else user.tenant.branches.filter(is_main_branch=True).first()
        
        # Check if user has an active shift
        active_shift = Shift.objects.filter(user=user, is_closed=False).first()
        if active_shift:
            return JsonResponse({'error': 'You already have an active shift'}, status=400)
        
        # Generate shift number
        shift_number = f"SHIFT-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
        
        shift = Shift.objects.create(
            tenant=user.tenant,
            branch=branch,
            user=user,
            shift_number=shift_number,
            opening_cash=opening_cash,
            opening_notes=opening_notes
        )
        
        return JsonResponse({
            'success': True,
            'shift_id': str(shift.id),
            'shift_number': shift_number
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def close_shift(request):
    """Close cashier shift"""
    try:
        data = json.loads(request.body)
        shift_id = data.get('shift_id')
        closing_cash = Decimal(str(data.get('closing_cash', 0)))
        closing_notes = data.get('closing_notes', '')
        
        user = request.user
        shift = get_object_or_404(Shift, id=shift_id, user=user, is_closed=False)
        
        # Calculate shift totals
        shift_sales = Sale.objects.filter(
            branch=shift.branch,
            created_by=user,
            created_at__gte=shift.opening_time,
            created_at__lte=timezone.now()
        ).aggregate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('id'),
            cash_sales=Sum('payments__amount', filter=Q(payments__payment_method='cash')),
            mpesa_sales=Sum('payments__amount', filter=Q(payments__payment_method='mpesa')),
            card_sales=Sum('payments__amount', filter=Q(payments__payment_method='card'))
        )
        
        shift.closing_time = timezone.now()
        shift.closing_cash = closing_cash
        shift.closing_notes = closing_notes
        shift.total_sales = shift_sales['total_sales'] or Decimal('0')
        shift.total_transactions = shift_sales['total_transactions'] or 0
        shift.cash_sales = shift_sales['cash_sales'] or Decimal('0')
        shift.mpesa_sales = shift_sales['mpesa_sales'] or Decimal('0')
        shift.card_sales = shift_sales['card_sales'] or Decimal('0')
        
        # Calculate expected cash
        shift.expected_cash = shift.opening_cash + shift.cash_sales
        shift.cash_difference = closing_cash - shift.expected_cash
        shift.is_closed = True
        shift.save()
        
        return JsonResponse({
            'success': True,
            'shift_summary': {
                'total_sales': float(shift.total_sales),
                'total_transactions': shift.total_transactions,
                'cash_difference': float(shift.cash_difference)
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)