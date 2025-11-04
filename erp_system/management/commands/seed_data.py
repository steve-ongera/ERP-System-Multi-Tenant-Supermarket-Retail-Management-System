"""
Django management command to seed the database with realistic sample data
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
import random

from erp_system.models import (
    Tenant, Branch, User, Category, Supplier, Product, Stock, StockMovement,
    PurchaseOrder, PurchaseOrderItem, Customer, Sale, SaleItem, Payment
)


class Command(BaseCommand):
    help = 'Seeds the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))

        # Create data in order of dependencies
        tenant = self.create_tenant()
        branches = self.create_branches(tenant)
        users = self.create_users(tenant, branches)
        categories = self.create_categories(tenant)
        suppliers = self.create_suppliers(tenant)
        products = self.create_products(tenant, categories, suppliers)
        self.create_stock(products, branches)
        customers = self.create_customers(tenant)
        purchase_orders = self.create_purchase_orders(tenant, branches[0], suppliers, products, users[0])
        sales = self.create_sales(tenant, branches, customers, products, users)
        self.create_payments(tenant, sales, customers, users)

        self.stdout.write(self.style.SUCCESS('✓ Data seeding completed successfully!'))
        self.print_summary()

    def clear_data(self):
        """Clear all existing data"""
        Payment.objects.all().delete()
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        Customer.objects.all().delete()
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        StockMovement.objects.all().delete()
        Stock.objects.all().delete()
        Product.objects.all().delete()
        Supplier.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(user_type__in=['tenant_admin', 'branch_manager', 'cashier', 'inventory_manager', 'sales_staff', 'accountant']).delete()
        Branch.objects.all().delete()
        Tenant.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✓ Existing data cleared'))

    def create_tenant(self):
        """Create a sample tenant"""
        self.stdout.write('Creating tenant...')
        tenant = Tenant.objects.create(
            business_name='Nairobi SuperMart',
            slug='nairobi-supermart',
            business_type='supermarket',
            registration_number='PVT-123456',
            tax_id='A001234567P',
            phone='+254712345678',
            email='info@nairobisupermart.co.ke',
            website='https://nairobisupermart.co.ke',
            physical_address='Kimathi Street, City Center',
            city='Nairobi',
            county='Nairobi',
            postal_code='00100',
            subscription_plan='premium',
            subscription_end=timezone.now() + timedelta(days=365),
            is_active=True,
            currency='KES',
            timezone='Africa/Nairobi',
            primary_color='#007bff'
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Created tenant: {tenant.business_name}'))
        return tenant

    def create_branches(self, tenant):
        """Create sample branches"""
        self.stdout.write('Creating branches...')
        branches_data = [
            {
                'name': 'Main Branch - CBD',
                'code': 'NB-001',
                'phone': '+254712345678',
                'email': 'cbd@nairobisupermart.co.ke',
                'physical_address': 'Kimathi Street, City Center',
                'city': 'Nairobi',
                'county': 'Nairobi',
                'is_main_branch': True
            },
            {
                'name': 'Westlands Branch',
                'code': 'NB-002',
                'phone': '+254712345679',
                'email': 'westlands@nairobisupermart.co.ke',
                'physical_address': 'Waiyaki Way, Westlands',
                'city': 'Nairobi',
                'county': 'Nairobi',
                'is_main_branch': False
            },
            {
                'name': 'Karen Branch',
                'code': 'NB-003',
                'phone': '+254712345680',
                'email': 'karen@nairobisupermart.co.ke',
                'physical_address': 'Karen Road, Karen',
                'city': 'Nairobi',
                'county': 'Nairobi',
                'is_main_branch': False
            }
        ]

        branches = []
        for data in branches_data:
            branch = Branch.objects.create(tenant=tenant, **data)
            branches.append(branch)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created branch: {branch.name}'))

        return branches

    def create_users(self, tenant, branches):
        """Create sample users"""
        self.stdout.write('Creating users...')
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@nairobisupermart.co.ke',
                'first_name': 'John',
                'last_name': 'Kamau',
                'user_type': 'tenant_admin',
                'phone': '+254712345681',
                'employee_id': 'EMP-001',
                'branch': branches[0]
            },
            {
                'username': 'manager_westlands',
                'email': 'manager.westlands@nairobisupermart.co.ke',
                'first_name': 'Mary',
                'last_name': 'Wanjiku',
                'user_type': 'branch_manager',
                'phone': '+254712345682',
                'employee_id': 'EMP-002',
                'branch': branches[1]
            },
            {
                'username': 'cashier1',
                'email': 'cashier1@nairobisupermart.co.ke',
                'first_name': 'Peter',
                'last_name': 'Omondi',
                'user_type': 'cashier',
                'phone': '+254712345683',
                'employee_id': 'EMP-003',
                'branch': branches[0]
            },
            {
                'username': 'cashier2',
                'email': 'cashier2@nairobisupermart.co.ke',
                'first_name': 'Jane',
                'last_name': 'Akinyi',
                'user_type': 'cashier',
                'phone': '+254712345684',
                'employee_id': 'EMP-004',
                'branch': branches[1]
            },
            {
                'username': 'inventory_manager',
                'email': 'inventory@nairobisupermart.co.ke',
                'first_name': 'David',
                'last_name': 'Mwangi',
                'user_type': 'inventory_manager',
                'phone': '+254712345685',
                'employee_id': 'EMP-005',
                'branch': branches[0]
            }
        ]

        users = []
        for data in users_data:
            user = User.objects.create(
                tenant=tenant,
                password=make_password('password123'),
                is_staff=True if data['user_type'] in ['tenant_admin', 'branch_manager'] else False,
                is_active=True,
                **data
            )
            users.append(user)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created user: {user.username} ({user.user_type})'))

        return users

    def create_categories(self, tenant):
        """Create product categories"""
        self.stdout.write('Creating categories...')
        categories_data = [
            {'name': 'Beverages', 'slug': 'beverages'},
            {'name': 'Dairy & Eggs', 'slug': 'dairy-eggs'},
            {'name': 'Bakery', 'slug': 'bakery'},
            {'name': 'Fresh Produce', 'slug': 'fresh-produce'},
            {'name': 'Meat & Poultry', 'slug': 'meat-poultry'},
            {'name': 'Snacks', 'slug': 'snacks'},
            {'name': 'Household', 'slug': 'household'},
            {'name': 'Personal Care', 'slug': 'personal-care'},
        ]

        categories = []
        for data in categories_data:
            category = Category.objects.create(
                tenant=tenant,
                is_active=True,
                **data
            )
            categories.append(category)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created category: {category.name}'))

        return categories

    def create_suppliers(self, tenant):
        """Create suppliers"""
        self.stdout.write('Creating suppliers...')
        suppliers_data = [
            {
                'name': 'Coca-Cola East Africa',
                'code': 'SUP-001',
                'contact_person': 'James Ochieng',
                'phone': '+254720111222',
                'email': 'sales@coca-cola.co.ke',
                'city': 'Nairobi',
                'payment_terms': 'Net 30',
                'credit_limit': Decimal('500000.00')
            },
            {
                'name': 'Brookside Dairy',
                'code': 'SUP-002',
                'contact_person': 'Sarah Njeri',
                'phone': '+254720222333',
                'email': 'orders@brookside.co.ke',
                'city': 'Ruiru',
                'payment_terms': 'Net 14',
                'credit_limit': Decimal('300000.00')
            },
            {
                'name': 'Kenya Bakeries Limited',
                'code': 'SUP-003',
                'contact_person': 'Michael Kimani',
                'phone': '+254720333444',
                'email': 'sales@kenyabakeries.co.ke',
                'city': 'Nairobi',
                'payment_terms': 'Net 7',
                'credit_limit': Decimal('200000.00')
            },
            {
                'name': 'Fresh Produce Suppliers Ltd',
                'code': 'SUP-004',
                'contact_person': 'Lucy Wambui',
                'phone': '+254720444555',
                'email': 'info@freshproduce.co.ke',
                'city': 'Thika',
                'payment_terms': 'COD',
                'credit_limit': Decimal('100000.00')
            },
            {
                'name': 'Unilever Kenya',
                'code': 'SUP-005',
                'contact_person': 'Robert Kipchoge',
                'phone': '+254720555666',
                'email': 'customer.service@unilever.co.ke',
                'city': 'Nairobi',
                'payment_terms': 'Net 30',
                'credit_limit': Decimal('400000.00')
            }
        ]

        suppliers = []
        for data in suppliers_data:
            supplier = Supplier.objects.create(
                tenant=tenant,
                is_active=True,
                **data
            )
            suppliers.append(supplier)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created supplier: {supplier.name}'))

        return suppliers

    def create_products(self, tenant, categories, suppliers):
        """Create 20 real products"""
        self.stdout.write('Creating products...')
        
        # Map categories by slug for easy access
        cat_dict = {cat.slug: cat for cat in categories}
        
        products_data = [
            # Beverages
            {'name': 'Coca-Cola 500ml', 'sku': 'BEV-001', 'barcode': '5449000000996', 'category': cat_dict['beverages'], 'supplier': suppliers[0], 'cost_price': Decimal('45.00'), 'selling_price': Decimal('60.00'), 'unit_of_measure': 'piece', 'reorder_level': 100, 'reorder_quantity': 500},
            {'name': 'Fanta Orange 500ml', 'sku': 'BEV-002', 'barcode': '5449000017505', 'category': cat_dict['beverages'], 'supplier': suppliers[0], 'cost_price': Decimal('45.00'), 'selling_price': Decimal('60.00'), 'unit_of_measure': 'piece', 'reorder_level': 100, 'reorder_quantity': 500},
            {'name': 'Sprite 500ml', 'sku': 'BEV-003', 'barcode': '5449000054227', 'category': cat_dict['beverages'], 'supplier': suppliers[0], 'cost_price': Decimal('45.00'), 'selling_price': Decimal('60.00'), 'unit_of_measure': 'piece', 'reorder_level': 100, 'reorder_quantity': 500},
            {'name': 'Minute Maid Orange Juice 1L', 'sku': 'BEV-004', 'barcode': '5060122030502', 'category': cat_dict['beverages'], 'supplier': suppliers[0], 'cost_price': Decimal('180.00'), 'selling_price': Decimal('220.00'), 'unit_of_measure': 'piece', 'reorder_level': 50, 'reorder_quantity': 200},
            
            # Dairy & Eggs
            {'name': 'Brookside Milk 500ml', 'sku': 'DAI-001', 'barcode': '6001087335805', 'category': cat_dict['dairy-eggs'], 'supplier': suppliers[1], 'cost_price': Decimal('55.00'), 'selling_price': Decimal('70.00'), 'unit_of_measure': 'piece', 'reorder_level': 80, 'reorder_quantity': 300},
            {'name': 'Brookside Yoghurt 500ml', 'sku': 'DAI-002', 'barcode': '6001087336109', 'category': cat_dict['dairy-eggs'], 'supplier': suppliers[1], 'cost_price': Decimal('85.00'), 'selling_price': Decimal('110.00'), 'unit_of_measure': 'piece', 'reorder_level': 60, 'reorder_quantity': 200},
            {'name': 'Fresh Eggs (Tray of 30)', 'sku': 'DAI-003', 'barcode': '2000000123456', 'category': cat_dict['dairy-eggs'], 'supplier': suppliers[1], 'cost_price': Decimal('380.00'), 'selling_price': Decimal('450.00'), 'unit_of_measure': 'piece', 'reorder_level': 30, 'reorder_quantity': 100},
            {'name': 'Cheese Slices 200g', 'sku': 'DAI-004', 'barcode': '6001087337106', 'category': cat_dict['dairy-eggs'], 'supplier': suppliers[1], 'cost_price': Decimal('250.00'), 'selling_price': Decimal('320.00'), 'unit_of_measure': 'piece', 'reorder_level': 40, 'reorder_quantity': 150},
            
            # Bakery
            {'name': 'White Bread 400g', 'sku': 'BAK-001', 'barcode': '6001024000101', 'category': cat_dict['bakery'], 'supplier': suppliers[2], 'cost_price': Decimal('38.00'), 'selling_price': Decimal('50.00'), 'unit_of_measure': 'piece', 'reorder_level': 50, 'reorder_quantity': 200},
            {'name': 'Brown Bread 400g', 'sku': 'BAK-002', 'barcode': '6001024000202', 'category': cat_dict['bakery'], 'supplier': suppliers[2], 'cost_price': Decimal('42.00'), 'selling_price': Decimal('55.00'), 'unit_of_measure': 'piece', 'reorder_level': 50, 'reorder_quantity': 200},
            {'name': 'Wheat Chapati (Pack of 10)', 'sku': 'BAK-003', 'barcode': '6001024000303', 'category': cat_dict['bakery'], 'supplier': suppliers[2], 'cost_price': Decimal('120.00'), 'selling_price': Decimal('150.00'), 'unit_of_measure': 'pack', 'reorder_level': 30, 'reorder_quantity': 100},
            
            # Fresh Produce
            {'name': 'Tomatoes (per kg)', 'sku': 'PRO-001', 'barcode': '2000001000001', 'category': cat_dict['fresh-produce'], 'supplier': suppliers[3], 'cost_price': Decimal('80.00'), 'selling_price': Decimal('120.00'), 'unit_of_measure': 'kg', 'reorder_level': 20, 'reorder_quantity': 50},
            {'name': 'Onions (per kg)', 'sku': 'PRO-002', 'barcode': '2000001000002', 'category': cat_dict['fresh-produce'], 'supplier': suppliers[3], 'cost_price': Decimal('70.00'), 'selling_price': Decimal('100.00'), 'unit_of_measure': 'kg', 'reorder_level': 20, 'reorder_quantity': 50},
            {'name': 'Potatoes (per kg)', 'sku': 'PRO-003', 'barcode': '2000001000003', 'category': cat_dict['fresh-produce'], 'supplier': suppliers[3], 'cost_price': Decimal('60.00'), 'selling_price': Decimal('90.00'), 'unit_of_measure': 'kg', 'reorder_level': 30, 'reorder_quantity': 100},
            {'name': 'Cabbage (per kg)', 'sku': 'PRO-004', 'barcode': '2000001000004', 'category': cat_dict['fresh-produce'], 'supplier': suppliers[3], 'cost_price': Decimal('40.00'), 'selling_price': Decimal('65.00'), 'unit_of_measure': 'kg', 'reorder_level': 25, 'reorder_quantity': 75},
            
            # Snacks
            {'name': 'Pringles Original 165g', 'sku': 'SNK-001', 'barcode': '5053990101634', 'category': cat_dict['snacks'], 'supplier': suppliers[4], 'cost_price': Decimal('280.00'), 'selling_price': Decimal('350.00'), 'unit_of_measure': 'piece', 'reorder_level': 40, 'reorder_quantity': 150},
            
            # Household
            {'name': 'OMO Detergent 1kg', 'sku': 'HOU-001', 'barcode': '6001087003162', 'category': cat_dict['household'], 'supplier': suppliers[4], 'cost_price': Decimal('320.00'), 'selling_price': Decimal('400.00'), 'unit_of_measure': 'piece', 'reorder_level': 30, 'reorder_quantity': 100},
            {'name': 'Vim Dish Wash 500ml', 'sku': 'HOU-002', 'barcode': '6001087006019', 'category': cat_dict['household'], 'supplier': suppliers[4], 'cost_price': Decimal('85.00'), 'selling_price': Decimal('120.00'), 'unit_of_measure': 'piece', 'reorder_level': 40, 'reorder_quantity': 150},
            
            # Personal Care
            {'name': 'Colgate Toothpaste 75ml', 'sku': 'PER-001', 'barcode': '6001067011003', 'category': cat_dict['personal-care'], 'supplier': suppliers[4], 'cost_price': Decimal('110.00'), 'selling_price': Decimal('145.00'), 'unit_of_measure': 'piece', 'reorder_level': 50, 'reorder_quantity': 200},
            {'name': 'Dettol Soap 175g', 'sku': 'PER-002', 'barcode': '6001106129606', 'category': cat_dict['personal-care'], 'supplier': suppliers[4], 'cost_price': Decimal('55.00'), 'selling_price': Decimal('75.00'), 'unit_of_measure': 'piece', 'reorder_level': 60, 'reorder_quantity': 200},
        ]

        products = []
        for data in products_data:
            product = Product.objects.create(
                tenant=tenant,
                is_active=True,
                is_featured=random.choice([True, False]),
                track_inventory=True,
                tax_percentage=Decimal('16.00'),
                is_tax_inclusive=True,
                **data
            )
            products.append(product)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created product: {product.name}'))

        return products

    def create_stock(self, products, branches):
        """Create stock for products across branches"""
        self.stdout.write('Creating stock records...')
        for product in products:
            for branch in branches:
                quantity = random.randint(50, 500)
                Stock.objects.create(
                    product=product,
                    branch=branch,
                    quantity=quantity,
                    reserved_quantity=random.randint(0, 10),
                    last_restocked=timezone.now() - timedelta(days=random.randint(1, 30))
                )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created stock for {len(products)} products across {len(branches)} branches'))

    def create_customers(self, tenant):
        """Create sample customers"""
        self.stdout.write('Creating customers...')
        customers_data = [
            {'customer_code': 'CUST-001', 'first_name': 'Alice', 'last_name': 'Wanjiru', 'phone': '+254722111222', 'email': 'alice.wanjiru@email.com', 'customer_type': 'retail', 'city': 'Nairobi'},
            {'customer_code': 'CUST-002', 'first_name': 'Bob', 'last_name': 'Otieno', 'phone': '+254722222333', 'email': 'bob.otieno@email.com', 'customer_type': 'retail', 'city': 'Nairobi'},
            {'customer_code': 'CUST-003', 'first_name': 'Carol', 'last_name': 'Muthoni', 'phone': '+254722333444', 'email': 'carol.muthoni@email.com', 'customer_type': 'vip', 'city': 'Nairobi', 'credit_limit': Decimal('50000.00'), 'loyalty_points': 1500},
            {'customer_code': 'CUST-004', 'first_name': 'Daniel', 'last_name': 'Kiprop', 'phone': '+254722444555', 'email': 'daniel.kiprop@email.com', 'customer_type': 'wholesale', 'city': 'Nairobi', 'credit_limit': Decimal('100000.00')},
            {'customer_code': 'CUST-005', 'first_name': 'Emily', 'last_name': 'Achieng', 'phone': '+254722555666', 'email': 'emily.achieng@email.com', 'customer_type': 'retail', 'city': 'Nairobi'},
            {'customer_code': 'CUST-006', 'first_name': 'Frank', 'last_name': 'Njoroge', 'phone': '+254722666777', 'customer_type': 'retail', 'city': 'Nairobi'},
            {'customer_code': 'CUST-007', 'first_name': 'Grace', 'last_name': 'Chebet', 'phone': '+254722777888', 'email': 'grace.chebet@email.com', 'customer_type': 'vip', 'city': 'Nairobi', 'loyalty_points': 800},
            {'customer_code': 'CUST-008', 'first_name': 'Henry', 'last_name': 'Mwangi', 'phone': '+254722888999', 'customer_type': 'retail', 'city': 'Nairobi'},
        ]

        customers = []
        for data in customers_data:
            customer = Customer.objects.create(
                tenant=tenant,
                is_active=True,
                **data
            )
            customers.append(customer)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created customer: {customer.first_name} {customer.last_name}'))

        return customers

    def create_purchase_orders(self, tenant, branch, suppliers, products, user):
        """Create sample purchase orders"""
        self.stdout.write('Creating purchase orders...')
        purchase_orders = []
        
        for i in range(3):
            supplier = random.choice(suppliers)
            po = PurchaseOrder.objects.create(
                tenant=tenant,
                branch=branch,
                supplier=supplier,
                po_number=f'PO-2024-{str(i+1).zfill(4)}',
                status=random.choice(['approved', 'ordered', 'completed']),
                order_date=date.today() - timedelta(days=random.randint(5, 30)),
                expected_delivery_date=date.today() + timedelta(days=random.randint(1, 14)),
                created_by=user
            )
            
            # Add items to purchase order
            subtotal = Decimal('0.00')
            selected_products = random.sample(products, k=random.randint(3, 8))
            
            for product in selected_products:
                quantity = random.randint(50, 200)
                unit_price = product.cost_price
                item_subtotal = Decimal(quantity) * unit_price
                
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity_ordered=quantity,
                    quantity_received=quantity if po.status == 'completed' else random.randint(0, quantity),
                    unit_price=unit_price,
                    subtotal=item_subtotal
                )
                subtotal += item_subtotal
            
            # Update PO totals
            tax_amount = subtotal * Decimal('0.16')
            po.subtotal = subtotal
            po.tax_amount = tax_amount
            po.total_amount = subtotal + tax_amount
            po.save()
            
            purchase_orders.append(po)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created purchase order: {po.po_number}'))

        return purchase_orders

    def create_sales(self, tenant, branches, customers, products, users):
        """Create sample sales"""
        self.stdout.write('Creating sales...')
        sales = []
        cashiers = [u for u in users if u.user_type == 'cashier']
        
        # Create sales for the past 30 days
        for day_offset in range(30):
            sale_date = timezone.now() - timedelta(days=day_offset)
            num_sales = random.randint(5, 15)
            
            for sale_num in range(num_sales):
                branch = random.choice(branches)
                cashier = random.choice(cashiers)
                customer = random.choice(customers) if random.random() > 0.3 else None
                
                sale = Sale.objects.create(
                    tenant=tenant,
                    branch=branch,
                    customer=customer,
                    invoice_number=f'INV-{sale_date.strftime("%Y%m%d")}-{str(sale_num+1).zfill(4)}',
                    receipt_number=f'REC-{sale_date.strftime("%Y%m%d")}-{str(sale_num+1).zfill(4)}',
                    payment_status='paid',
                    sale_type='pos',
                    sale_date=sale_date,
                    created_by=cashier
                )
                
                # Add items to sale
                subtotal = Decimal('0.00')
                selected_products = random.sample(products, k=random.randint(2, 8))
                
                for product in selected_products:
                    quantity = random.randint(1, 5)
                    unit_price = product.selling_price
                    discount = Decimal('0.00')
                    item_subtotal = (Decimal(quantity) * unit_price) * (Decimal('1') - discount / Decimal('100'))
                    
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        discount_percentage=discount,
                        tax_percentage=Decimal('16.00'),
                        subtotal=item_subtotal
                    )
                    subtotal += item_subtotal
                
                # Update sale totals
                tax_amount = subtotal * Decimal('0.16') / Decimal('1.16')  # Tax inclusive
                sale.subtotal = subtotal - tax_amount
                sale.tax_amount = tax_amount
                sale.total_amount = subtotal
                sale.amount_paid = subtotal
                sale.change_given = Decimal('0.00')
                sale.save()
                
                sales.append(sale)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(sales)} sales records'))
        return sales

    def create_payments(self, tenant, sales, customers, users):
        """Create payments for sales"""
        self.stdout.write('Creating payments...')
        for sale in sales:
            Payment.objects.create(
                tenant=tenant,
                sale=sale,
                payment_date=sale.sale_date,
                amount=sale.amount_paid,
                payment_method=random.choice(['cash', 'mpesa', 'credit_card']),
                received_by=random.choice([u for u in users if u.user_type in ['cashier', 'accountant']])
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created payments for {len(sales)} sales'))
    def print_summary(self):
        """Print a summary of created records"""
        self.stdout.write('\nData Seeding Summary:')
        self.stdout.write(f'  Tenants: {Tenant.objects.count()}')
        self.stdout.write(f'  Branches: {Branch.objects.count()}')
        self.stdout.write(f'  Users: {User.objects.filter(user_type__in=["tenant_admin", "branch_manager", "cashier", "inventory_manager", "sales_staff", "accountant"]).count()}')
        self.stdout.write(f'  Categories: {Category.objects.count()}')
        self.stdout.write(f'  Suppliers: {Supplier.objects.count()}')
        self.stdout.write(f'  Products: {Product.objects.count()}')
        self.stdout.write(f'  Stock Records: {Stock.objects.count()}')
        self.stdout.write(f'  Customers: {Customer.objects.count()}')
        self.stdout.write(f'  Purchase Orders: {PurchaseOrder.objects.count()}')
        self.stdout.write(f'  Sales: {Sale.objects.count()}')
        self.stdout.write(f'  Payments: {Payment.objects.count()}')