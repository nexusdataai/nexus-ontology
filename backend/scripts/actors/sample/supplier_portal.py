#!/usr/bin/env python3
# supplier_portal.py
"""
E-commerce - Supplier Portal
Complete supplier management, procurement, billing, and analytics
Handles: Supplier onboarding, Purchase Orders, Invoices, Payments, Performance tracking
"""

import boto3
import sys
import getpass
import os
import json
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional


class SupplierPortal:
    """E-commerce Supplier Portal - Complete Procurement Management"""
    
    def __init__(self):
        self.region_name = 'ap-south-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Aurora Spark Theme Optimized Tables
        self.users_table = self.dynamodb.Table('AuroraSparkTheme-Users')
        self.products_table = self.dynamodb.Table('AuroraSparkTheme-Products')
        self.suppliers_table = self.dynamodb.Table('AuroraSparkTheme-Suppliers')
        self.procurement_table = self.dynamodb.Table('AuroraSparkTheme-Procurement')
        self.inventory_table = self.dynamodb.Table('AuroraSparkTheme-Inventory')
        self.analytics_table = self.dynamodb.Table('AuroraSparkTheme-Analytics')
        self.system_table = self.dynamodb.Table('AuroraSparkTheme-System')
        
        self.current_user = None
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 100)
        print(f"🏪 [E-COMMERCE - SUPPLIER PORTAL] {title}")
        print("=" * 100)
        
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ [SUCCESS] {message}")
        
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ [ERROR] {message}")
        
    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  [INFO] {message}")
        
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  [WARNING] {message}")

    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, email: str, password: str) -> bool:
        """Authenticate supplier manager"""
        try:
            # Query users table by email
            response = self.users_table.query(
                IndexName='EmailIndex',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            users = response.get('Items', [])
            if not users:
                self.print_error("User not found")
                return False
                
            user = users[0]
            hashed_password = self.hash_password(password)
            
            if user.get('passwordHash') != hashed_password:
                self.print_error("Invalid password")
                return False
                
            if user.get('status') != 'active':
                self.print_error("User account is not active")
                return False
            
            # Check if user has supplier manager role
            user_roles = user.get('roles', [])
            allowed_roles = ['supplier_manager', 'super_admin']
            
            if not any(role in user_roles for role in allowed_roles):
                self.print_error("Access denied. Supplier management role required.")
                return False
            
            self.current_user = user
            
            # Update last login
            self.users_table.update_item(
                Key={'userID': user['userID'], 'email': user['email']},
                UpdateExpression='SET lastLogin = :login_time, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':login_time': datetime.now(timezone.utc).isoformat(),
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            role_name = user.get('primaryRole', 'supplier_manager').replace('_', ' ').title()
            self.print_success(f"Welcome, {user['firstName']} {user['lastName']} ({role_name})!")
            return True
            
        except Exception as e:
            self.print_error(f"Authentication failed: {str(e)}")
            return False

    def display_supplier_dashboard(self):
        """Display comprehensive supplier management dashboard"""
        self.print_header("SUPPLIER MANAGEMENT DASHBOARD")
        
        try:
            # Suppliers Overview
            print("🏪 SUPPLIERS OVERVIEW:")
            print("-" * 60)
            
            try:
                suppliers_response = self.suppliers_table.scan()
                suppliers = suppliers_response.get('Items', [])
                
                total_suppliers = len(suppliers)
                active_suppliers = len([s for s in suppliers if s.get('status') == 'active'])
                pending_suppliers = len([s for s in suppliers if s.get('status') == 'pending'])
                
                print(f"🏪 Total Suppliers: {total_suppliers:,}")
                print(f"✅ Active Suppliers: {active_suppliers:,}")
                print(f"⏳ Pending Approval: {pending_suppliers:,}")
                
                # Calculate performance metrics
                if suppliers:
                    total_rating = sum(float(s.get('performance', {}).get('rating', 0)) for s in suppliers)
                    avg_rating = total_rating / len(suppliers) if suppliers else 0
                    
                    total_value = sum(Decimal(str(s.get('performance', {}).get('totalValue', 0))) for s in suppliers)
                    
                    print(f"⭐ Average Rating: {avg_rating:.2f}/5.0")
                    print(f"💰 Total Supplier Value: ₹{total_value:,.2f}")
                    
                    # Top suppliers
                    top_suppliers = sorted(suppliers, 
                                         key=lambda x: float(x.get('performance', {}).get('rating', 0)), 
                                         reverse=True)[:3]
                    
                    print(f"\n🏆 TOP SUPPLIERS:")
                    for i, supplier in enumerate(top_suppliers, 1):
                        rating = supplier.get('performance', {}).get('rating', 0)
                        print(f"   {i}. {supplier.get('name', 'Unknown')} - {rating}/5.0")
                
            except Exception as e:
                print(f"❌ Error loading supplier data: {str(e)}")
            
            # Procurement Overview
            print(f"\n📋 PROCUREMENT OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get purchase orders
                po_response = self.procurement_table.query(
                    IndexName='TypeIndex',
                    KeyConditionExpression='documentType = :doc_type',
                    ExpressionAttributeValues={':doc_type': 'purchase_order'}
                )
                
                purchase_orders = po_response.get('Items', [])
                
                if purchase_orders:
                    active_pos = len([po for po in purchase_orders if po.get('status') in ['sent', 'confirmed', 'partially_received']])
                    total_po_value = sum(Decimal(str(po.get('finalAmount', 0))) for po in purchase_orders)
                    
                    print(f"📋 Total Purchase Orders: {len(purchase_orders):,}")
                    print(f"🔄 Active Orders: {active_pos:,}")
                    print(f"💰 Total PO Value: ₹{total_po_value:,.2f}")
                    
                    # Status breakdown
                    status_counts = {}
                    for po in purchase_orders:
                        status = po.get('status', 'unknown')
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    print(f"\n📊 PO Status Breakdown:")
                    status_emojis = {
                        'draft': '📝',
                        'sent': '📤',
                        'confirmed': '✅',
                        'partially_received': '📦',
                        'received': '✅',
                        'cancelled': '❌'
                    }
                    
                    for status, count in status_counts.items():
                        emoji = status_emojis.get(status, '❓')
                        print(f"   {emoji} {status.replace('_', ' ').title()}: {count}")
                else:
                    print("📋 No purchase orders found")
                
            except Exception as e:
                print(f"❌ Error loading procurement data: {str(e)}")
            
            # Payment Overview
            print(f"\n💰 PAYMENTS OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get payments
                payment_response = self.procurement_table.query(
                    IndexName='TypeIndex',
                    KeyConditionExpression='documentType = :doc_type',
                    ExpressionAttributeValues={':doc_type': 'payment'}
                )
                
                payments = payment_response.get('Items', [])
                
                if payments:
                    pending_payments = len([p for p in payments if p.get('status') == 'pending'])
                    completed_payments = len([p for p in payments if p.get('status') == 'completed'])
                    total_paid = sum(Decimal(str(p.get('amount', 0))) for p in payments if p.get('status') == 'completed')
                    total_pending = sum(Decimal(str(p.get('amount', 0))) for p in payments if p.get('status') == 'pending')
                    
                    print(f"💳 Total Payments: {len(payments):,}")
                    print(f"⏳ Pending: {pending_payments:,} (₹{total_pending:,.2f})")
                    print(f"✅ Completed: {completed_payments:,} (₹{total_paid:,.2f})")
                    
                    if pending_payments > 0:
                        print(f"🚨 Outstanding Amount: ₹{total_pending:,.2f}")
                else:
                    print("💰 No payment records found")
                
            except Exception as e:
                print(f"❌ Error loading payment data: {str(e)}")
            
            # Recent Activity
            print(f"\n📊 RECENT ACTIVITY:")
            print("-" * 60)
            
            try:
                # Get recent procurement documents
                recent_docs = self.procurement_table.scan(Limit=5)
                
                if recent_docs.get('Items'):
                    print("📋 Recent Procurement Activity:")
                    for doc in recent_docs['Items'][:5]:
                        doc_type = doc.get('documentType', 'unknown')
                        doc_emoji = {
                            'purchase_order': '📋',
                            'invoice': '📄',
                            'payment': '💰'
                        }.get(doc_type, '📄')
                        
                        print(f"   {doc_emoji} {doc_type.replace('_', ' ').title()}")
                        print(f"      ID: {doc.get('documentID', 'N/A')}")
                        print(f"      Date: {doc.get('documentDate', 'N/A')}")
                        print(f"      Status: {doc.get('status', 'N/A').title()}")
                else:
                    print("📋 No recent activity")
                
            except Exception as e:
                print(f"❌ Error loading recent activity: {str(e)}")
                
        except Exception as e:
            self.print_error(f"Failed to load dashboard: {str(e)}")

    def supplier_management(self):
        """Supplier management operations"""
        while True:
            self.print_header("SUPPLIER MANAGEMENT")
            print("🏪 SUPPLIER MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 📋 View All Suppliers")
            print("2. ➕ Add New Supplier")
            print("3. ✏️  Edit Supplier Details")
            print("4. 📊 Supplier Performance")
            print("5. ⭐ Supplier Reviews")
            print("6. 📂 Supplier Categories")
            print("7. ✅ Supplier Approvals")
            print("8. 🔄 Supplier Status Management")
            print("9. 📈 Supplier Analytics")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_suppliers()
            elif choice == '2':
                self.add_new_supplier()
            elif choice == '3':
                self.edit_supplier_details()
            elif choice == '4':
                self.supplier_performance()
            elif choice == '5':
                self.supplier_reviews()
            elif choice == '6':
                self.supplier_categories()
            elif choice == '7':
                self.supplier_approvals()
            elif choice == '8':
                self.supplier_status_management()
            elif choice == '9':
                self.supplier_analytics()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_suppliers(self):
        """View all suppliers with detailed information"""
        try:
            print("\n🏪 SUPPLIER DIRECTORY")
            print("=" * 100)
            
            response = self.suppliers_table.scan()
            suppliers = response.get('Items', [])
            
            if not suppliers:
                self.print_info("No suppliers found")
                return
            
            print(f"🏪 SUPPLIERS ({len(suppliers)} total):")
            print("-" * 100)
            
            for supplier in suppliers:
                contact_info = supplier.get('contactInfo', {})
                performance = supplier.get('performance', {})
                address = supplier.get('address', {})
                
                status_emoji = {
                    'active': '✅',
                    'inactive': '❌',
                    'pending': '⏳',
                    'suspended': '🚫'
                }.get(supplier.get('status', 'pending'), '❓')
                
                rating = float(performance.get('rating', 0))
                rating_stars = '⭐' * int(rating) + '☆' * (5 - int(rating))
                
                print(f"{status_emoji} {supplier.get('name', 'Unknown Supplier')}")
                print(f"   🏷️  Code: {supplier.get('supplierCode', 'N/A')}")
                print(f"   👤 Contact: {contact_info.get('contactPerson', 'N/A')}")
                print(f"   📧 Email: {contact_info.get('email', 'N/A')}")
                print(f"   📞 Phone: {contact_info.get('phone', 'N/A')}")
                print(f"   📍 Location: {address.get('city', 'N/A')}, {address.get('state', 'N/A')}")
                print(f"   {rating_stars} Rating: {rating:.1f}/5.0")
                print(f"   📦 Total Orders: {performance.get('totalOrders', 0):,}")
                print(f"   💰 Total Value: ₹{performance.get('totalValue', 0):,.2f}")
                print(f"   📊 On-time Rate: {performance.get('onTimeDeliveryRate', 0):.1f}%")
                print(f"   🌟 Quality Score: {performance.get('qualityScore', 0):.1f}/5.0")
                print(f"   📊 Status: {supplier.get('status', 'N/A').title()}")
                
                business_terms = supplier.get('businessTerms', {})
                if business_terms:
                    print(f"   💳 Payment Terms: {business_terms.get('paymentTerms', 'N/A')}")
                    print(f"   💰 Credit Limit: ₹{business_terms.get('creditLimit', 0):,.2f}")
                
                print("-" * 100)
                
        except Exception as e:
            self.print_error(f"Failed to load suppliers: {str(e)}")

    def add_new_supplier(self):
        """Add a new supplier"""
        try:
            print("\n➕ ADD NEW SUPPLIER")
            print("=" * 60)
            
            # Basic supplier information
            supplier_code = input("🏷️  Supplier Code: ").strip().upper()
            if not supplier_code:
                self.print_error("Supplier code is required")
                return
            
            # Check if supplier code already exists
            existing_check = self.suppliers_table.query(
                IndexName='CodeIndex',
                KeyConditionExpression='supplierCode = :code',
                ExpressionAttributeValues={':code': supplier_code}
            )
            
            if existing_check.get('Items'):
                self.print_error("Supplier code already exists")
                return
            
            name = input("🏪 Supplier Name: ").strip()
            contact_person = input("👤 Contact Person: ").strip()
            email = input("📧 Email: ").strip()
            phone = input("📞 Phone: ").strip()
            
            # Address information
            print("\n📍 ADDRESS INFORMATION:")
            street = input("🏠 Street Address: ").strip()
            city = input("🏙️  City: ").strip()
            state = input("🗺️  State: ").strip()
            postal_code = input("📮 Postal Code: ").strip()
            country = input("🌍 Country (default: India): ").strip() or "India"
            
            # Business information
            print("\n💼 BUSINESS INFORMATION:")
            print("📂 Supplier Category:")
            print("1. Organic Farms")
            print("2. Dairy Suppliers")
            print("3. Fruit Vendors")
            print("4. Vegetable Suppliers")
            print("5. Processed Foods")
            print("6. Other")
            
            category_choice = input("Select category (1-6): ").strip()
            categories = {
                '1': 'organic_farms',
                '2': 'dairy_suppliers',
                '3': 'fruit_vendors',
                '4': 'vegetable_suppliers',
                '5': 'processed_foods',
                '6': 'other'
            }
            category = categories.get(category_choice, 'other')
            
            print("\n💳 Payment Terms:")
            print("1. Net 15")
            print("2. Net 30")
            print("3. Net 45")
            print("4. Net 60")
            terms_choice = input("Select payment terms (1-4): ").strip()
            
            payment_terms = {
                '1': 'Net 15',
                '2': 'Net 30',
                '3': 'Net 45',
                '4': 'Net 60'
            }.get(terms_choice, 'Net 30')
            
            credit_limit = input("💰 Credit Limit (₹): ").strip()
            tax_id = input("🆔 Tax ID/GST Number: ").strip()
            
            # Banking information
            print("\n🏦 BANKING INFORMATION:")
            bank_name = input("🏦 Bank Name: ").strip()
            account_number = input("🔢 Account Number: ").strip()
            ifsc_code = input("🏛️  IFSC Code: ").strip()
            
            if not all([supplier_code, name, contact_person, email]):
                self.print_error("Supplier code, name, contact person, and email are required")
                return
            
            # Create supplier
            supplier_id = str(uuid.uuid4())
            
            supplier_data = {
                'supplierID': supplier_id,
                'supplierCode': supplier_code,
                'name': name,
                'contactInfo': {
                    'contactPerson': contact_person,
                    'email': email,
                    'phone': phone
                },
                'address': {
                    'street': street,
                    'city': city,
                    'state': state,
                    'postalCode': postal_code,
                    'country': country
                },
                'category': category,
                'categoryInfo': {
                    'categoryName': category.replace('_', ' ').title(),
                    'categoryColor': '#4CAF50'
                },
                'performance': {
                    'rating': Decimal('0.0'),
                    'totalOrders': 0,
                    'totalValue': Decimal('0.0'),
                    'onTimeDeliveryRate': Decimal('0.0'),
                    'qualityScore': Decimal('0.0')
                },
                'businessTerms': {
                    'paymentTerms': payment_terms,
                    'creditLimit': Decimal(credit_limit) if credit_limit else Decimal('0.0'),
                    'discountRate': Decimal('0.0')
                },
                'compliance': {
                    'taxID': tax_id,
                    'certifications': [],
                    'bankDetails': {
                        'accountNumber': account_number,
                        'ifscCode': ifsc_code,
                        'bankName': bank_name
                    }
                },
                'status': 'pending',  # Requires approval
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.suppliers_table.put_item(Item=supplier_data)
            
            # Log the action
            self.log_audit_event('CREATE_SUPPLIER', 'Supplier', supplier_id, 
                               f"Created new supplier: {name}")
            
            self.print_success(f"Supplier '{name}' added successfully!")
            print(f"🔑 Supplier ID: {supplier_id}")
            print(f"🏷️  Supplier Code: {supplier_code}")
            print(f"📊 Status: Pending Approval")
            print(f"💳 Payment Terms: {payment_terms}")
            
        except Exception as e:
            self.print_error(f"Failed to add supplier: {str(e)}")

    def procurement_management(self):
        """Purchase order management"""
        while True:
            self.print_header("PROCUREMENT MANAGEMENT")
            print("📋 PROCUREMENT MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 📋 View All Purchase Orders")
            print("2. ➕ Create New Purchase Order")
            print("3. ✏️  Edit Purchase Order")
            print("4. 📦 Receive Goods")
            print("5. 📊 PO Analytics")
            print("6. 🔍 Search Purchase Orders")
            print("7. 📈 Procurement Trends")
            print("8. ⚠️  Overdue Orders")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_purchase_orders()
            elif choice == '2':
                self.create_new_purchase_order()
            elif choice == '3':
                self.edit_purchase_order()
            elif choice == '4':
                self.receive_goods()
            elif choice == '5':
                self.po_analytics()
            elif choice == '6':
                self.search_purchase_orders()
            elif choice == '7':
                self.procurement_trends()
            elif choice == '8':
                self.overdue_orders()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_purchase_orders(self):
        """View all purchase orders"""
        try:
            print("\n📋 PURCHASE ORDERS")
            print("=" * 100)
            
            response = self.procurement_table.query(
                IndexName='TypeIndex',
                KeyConditionExpression='documentType = :doc_type',
                ExpressionAttributeValues={':doc_type': 'purchase_order'}
            )
            
            purchase_orders = response.get('Items', [])
            
            if not purchase_orders:
                self.print_info("No purchase orders found")
                return
            
            print(f"📋 PURCHASE ORDERS ({len(purchase_orders)} total):")
            print("-" * 100)
            
            for po in sorted(purchase_orders, key=lambda x: x.get('documentDate', ''), reverse=True):
                status_emoji = {
                    'draft': '📝',
                    'sent': '📤',
                    'confirmed': '✅',
                    'partially_received': '📦',
                    'received': '✅',
                    'cancelled': '❌'
                }.get(po.get('status', 'draft'), '📝')
                
                print(f"{status_emoji} PO #{po.get('poNumber', 'N/A')}")
                
                # Get supplier details
                supplier_id = po.get('supplierID')
                if supplier_id:
                    try:
                        supplier_response = self.suppliers_table.get_item(
                            Key={'supplierID': supplier_id, 'supplierCode': po.get('supplierCode', '')}
                        )
                        if 'Item' in supplier_response:
                            supplier = supplier_response['Item']
                            print(f"   🏪 Supplier: {supplier.get('name', 'Unknown')}")
                    except:
                        print(f"   🏪 Supplier ID: {supplier_id}")
                
                print(f"   📅 Order Date: {po.get('documentDate', 'N/A')}")
                print(f"   📦 Expected Delivery: {po.get('expectedDeliveryDate', 'N/A')}")
                print(f"   📊 Status: {po.get('status', 'N/A').title()}")
                print(f"   💰 Total Amount: ₹{po.get('totalAmount', 0):,.2f}")
                print(f"   💵 Final Amount: ₹{po.get('finalAmount', 0):,.2f}")
                
                if po.get('actualDeliveryDate'):
                    print(f"   ✅ Delivered: {po['actualDeliveryDate']}")
                
                # Show items if available
                items = po.get('items', [])
                if items:
                    print(f"   📦 Items ({len(items)}):")
                    for item in items[:3]:  # Show first 3 items
                        print(f"      • {item.get('productName', 'Unknown')} x {item.get('quantity', 0)}")
                    if len(items) > 3:
                        print(f"      • ... and {len(items) - 3} more items")
                
                print("-" * 100)
                
        except Exception as e:
            self.print_error(f"Failed to load purchase orders: {str(e)}")

    def create_new_purchase_order(self):
        """Create a new purchase order"""
        try:
            print("\n➕ CREATE NEW PURCHASE ORDER")
            print("=" * 60)
            
            # Select supplier
            print("🏪 SELECT SUPPLIER:")
            suppliers_response = self.suppliers_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'active'}
            )
            
            suppliers = suppliers_response.get('Items', [])
            
            if not suppliers:
                self.print_error("No active suppliers found. Please add suppliers first.")
                return
            
            print("Available Suppliers:")
            for i, supplier in enumerate(suppliers, 1):
                print(f"{i}. {supplier.get('name', 'Unknown')} ({supplier.get('supplierCode', 'N/A')})")
            
            supplier_choice = input(f"\nSelect supplier (1-{len(suppliers)}): ").strip()
            
            if not supplier_choice.isdigit() or not (1 <= int(supplier_choice) <= len(suppliers)):
                self.print_error("Invalid supplier selection")
                return
            
            selected_supplier = suppliers[int(supplier_choice) - 1]
            
            # PO details
            expected_delivery = input("📅 Expected Delivery Date (YYYY-MM-DD): ").strip()
            notes = input("📝 Notes (optional): ").strip()
            
            # Add items
            print("\n📦 ADD ITEMS TO PURCHASE ORDER:")
            items = []
            
            while True:
                print(f"\nItem {len(items) + 1}:")
                product_code = input("🏷️  Product Code (or 'done' to finish): ").strip()
                
                if product_code.lower() == 'done':
                    break
                
                # Find product
                product_response = self.products_table.query(
                    IndexName='CodeIndex',
                    KeyConditionExpression='productCode = :code',
                    ExpressionAttributeValues={':code': product_code}
                )
                
                products = product_response.get('Items', [])
                if not products:
                    self.print_error(f"Product with code '{product_code}' not found")
                    continue
                
                product = products[0]
                print(f"   📦 Product: {product.get('name', 'Unknown')}")
                
                # Handle variants if product has them
                variant_id = None
                if product.get('hasVariants'):
                    variants = product.get('variants', [])
                    if variants:
                        print(f"   🔄 Available Variants:")
                        for i, variant in enumerate(variants, 1):
                            print(f"   {i}. {variant.get('variantName', 'Unknown')}")
                        
                        variant_choice = input(f"   Select variant (1-{len(variants)}): ").strip()
                        if variant_choice.isdigit() and 1 <= int(variant_choice) <= len(variants):
                            selected_variant = variants[int(variant_choice) - 1]
                            variant_id = selected_variant.get('variantID')
                            print(f"   ✅ Selected: {selected_variant.get('variantName')}")
                
                quantity = input("📊 Quantity: ").strip()
                unit_price = input("💰 Unit Price: ").strip()
                
                if not all([quantity, unit_price]):
                    self.print_error("Quantity and unit price are required")
                    continue
                
                try:
                    qty = int(quantity)
                    price = Decimal(unit_price)
                    total_price = price * qty
                    
                    item = {
                        'itemID': str(uuid.uuid4()),
                        'productID': product.get('productID'),
                        'variantID': variant_id,
                        'productName': product.get('name'),
                        'variantName': selected_variant.get('variantName') if variant_id else None,
                        'quantity': qty,
                        'unit': product.get('unit', 'units'),
                        'unitPrice': price,
                        'totalPrice': total_price,
                        'receivedQuantity': 0,
                        'qualityGrade': None,
                        'batchNumber': None,
                        'notes': None
                    }
                    
                    items.append(item)
                    self.print_success(f"Added: {product.get('name')} x {qty} = ₹{total_price:.2f}")
                    
                except ValueError:
                    self.print_error("Invalid quantity or price format")
                    continue
            
            if not items:
                self.print_error("No items added to purchase order")
                return
            
            # Calculate totals
            subtotal = sum(item['totalPrice'] for item in items)
            tax_rate = Decimal('0.18')  # 18% GST
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            print(f"\n💰 ORDER SUMMARY:")
            print(f"   📊 Subtotal: ₹{subtotal:.2f}")
            print(f"   📊 Tax (18%): ₹{tax_amount:.2f}")
            print(f"   💰 Total: ₹{total_amount:.2f}")
            
            confirm = input("\n✅ Create purchase order? (y/n): ").strip().lower()
            if confirm != 'y':
                self.print_info("Purchase order cancelled")
                return
            
            # Create PO
            po_id = str(uuid.uuid4())
            po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            
            po_data = {
                'documentID': po_id,
                'documentType': 'purchase_order',
                'poNumber': po_number,
                'supplierID': selected_supplier.get('supplierID'),
                'supplierCode': selected_supplier.get('supplierCode'),
                'supplierName': selected_supplier.get('name'),
                'documentDate': datetime.now(timezone.utc).date().isoformat(),
                'expectedDeliveryDate': expected_delivery if expected_delivery else None,
                'actualDeliveryDate': None,
                'subtotal': subtotal,
                'taxAmount': tax_amount,
                'discountAmount': Decimal('0.0'),
                'totalAmount': subtotal,
                'finalAmount': total_amount,
                'status': 'draft',
                'paymentStatus': 'pending',
                'paymentMethod': None,
                'paymentDate': None,
                'notes': notes,
                'termsConditions': f"Payment Terms: {payment_terms}",
                'items': items,
                'createdBy': self.current_user['userID'],
                'approvedBy': None,
                'approvedAt': None,
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.procurement_table.put_item(Item=po_data)
            
            # Log the action
            self.log_audit_event('CREATE_PURCHASE_ORDER', 'PurchaseOrder', po_id, 
                               f"Created PO {po_number} for {selected_supplier.get('name')} - ₹{total_amount:.2f}")
            
            self.print_success(f"Purchase Order created successfully!")
            print(f"📋 PO Number: {po_number}")
            print(f"🏪 Supplier: {selected_supplier.get('name')}")
            print(f"💰 Total Amount: ₹{total_amount:.2f}")
            print(f"📦 Items: {len(items)}")
            print(f"📊 Status: Draft (Ready for approval)")
            
        except Exception as e:
            self.print_error(f"Failed to create purchase order: {str(e)}")

    def billing_management(self):
        """Billing and payment management"""
        while True:
            self.print_header("BILLING & PAYMENTS")
            print("💰 BILLING MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 📄 View All Invoices")
            print("2. ➕ Create New Invoice")
            print("3. 💳 Process Payments")
            print("4. 📊 Payment Reports")
            print("5. ⚠️  Outstanding Payments")
            print("6. 📈 Payment Analytics")
            print("7. 💰 Payment Methods")
            print("8. 🔍 Search Invoices")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_invoices()
            elif choice == '2':
                self.create_new_invoice()
            elif choice == '3':
                self.process_payments()
            elif choice == '4':
                self.payment_reports()
            elif choice == '5':
                self.outstanding_payments()
            elif choice == '6':
                self.payment_analytics()
            elif choice == '7':
                self.payment_methods()
            elif choice == '8':
                self.search_invoices()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_invoices(self):
        """View all invoices"""
        try:
            print("\n📄 INVOICES")
            print("=" * 100)
            
            response = self.procurement_table.query(
                IndexName='TypeIndex',
                KeyConditionExpression='documentType = :doc_type',
                ExpressionAttributeValues={':doc_type': 'invoice'}
            )
            
            invoices = response.get('Items', [])
            
            if not invoices:
                self.print_info("No invoices found")
                return
            
            print(f"📄 INVOICES ({len(invoices)} total):")
            print("-" * 100)
            
            for invoice in sorted(invoices, key=lambda x: x.get('documentDate', ''), reverse=True):
                status_emoji = {
                    'pending': '⏳',
                    'overdue': '🔴',
                    'paid': '✅',
                    'partial': '💰',
                    'cancelled': '❌'
                }.get(invoice.get('status', 'pending'), '⏳')
                
                print(f"{status_emoji} Invoice #{invoice.get('invoiceNumber', 'N/A')}")
                
                # Get supplier info
                supplier_id = invoice.get('supplierID')
                if supplier_id:
                    try:
                        supplier_response = self.suppliers_table.get_item(
                            Key={'supplierID': supplier_id, 'supplierCode': invoice.get('supplierCode', '')}
                        )
                        if 'Item' in supplier_response:
                            supplier = supplier_response['Item']
                            print(f"   🏪 Supplier: {supplier.get('name', 'Unknown')}")
                    except:
                        print(f"   🏪 Supplier ID: {supplier_id}")
                
                print(f"   📅 Invoice Date: {invoice.get('documentDate', 'N/A')}")
                print(f"   📅 Due Date: {invoice.get('dueDate', 'N/A')}")
                print(f"   📊 Status: {invoice.get('status', 'N/A').title()}")
                print(f"   💰 Total Amount: ₹{invoice.get('totalAmount', 0):,.2f}")
                print(f"   💵 Paid Amount: ₹{invoice.get('paidAmount', 0):,.2f}")
                print(f"   💸 Balance: ₹{invoice.get('balanceAmount', 0):,.2f}")
                
                if invoice.get('paymentTerms'):
                    print(f"   💳 Payment Terms: {invoice['paymentTerms']}")
                
                print("-" * 100)
                
        except Exception as e:
            self.print_error(f"Failed to load invoices: {str(e)}")

    def supplier_analytics(self):
        """Supplier analytics and performance tracking"""
        try:
            print("\n📊 SUPPLIER ANALYTICS")
            print("=" * 80)
            
            # Get all suppliers for analysis
            suppliers_response = self.suppliers_table.scan()
            suppliers = suppliers_response.get('Items', [])
            
            if not suppliers:
                self.print_info("No suppliers found for analysis")
                return
            
            # Overall supplier metrics
            total_suppliers = len(suppliers)
            active_suppliers = len([s for s in suppliers if s.get('status') == 'active'])
            total_value = sum(Decimal(str(s.get('performance', {}).get('totalValue', 0))) for s in suppliers)
            avg_rating = sum(float(s.get('performance', {}).get('rating', 0)) for s in suppliers) / total_suppliers if suppliers else 0
            
            print("📊 SUPPLIER PERFORMANCE SUMMARY:")
            print("-" * 60)
            print(f"🏪 Total Suppliers: {total_suppliers:,}")
            print(f"✅ Active Suppliers: {active_suppliers:,}")
            print(f"💰 Total Business Value: ₹{total_value:,.2f}")
            print(f"⭐ Average Rating: {avg_rating:.2f}/5.0")
            
            # Top performers
            top_by_rating = sorted(suppliers, 
                                 key=lambda x: float(x.get('performance', {}).get('rating', 0)), 
                                 reverse=True)[:5]
            
            print(f"\n🏆 TOP SUPPLIERS BY RATING:")
            print("-" * 60)
            for i, supplier in enumerate(top_by_rating, 1):
                performance = supplier.get('performance', {})
                rating = float(performance.get('rating', 0))
                total_orders = performance.get('totalOrders', 0)
                
                print(f"{i}. {supplier.get('name', 'Unknown')}")
                print(f"   ⭐ Rating: {rating:.1f}/5.0")
                print(f"   📦 Orders: {total_orders:,}")
                print(f"   💰 Value: ₹{performance.get('totalValue', 0):,.2f}")
                print(f"   📊 On-time Rate: {performance.get('onTimeDeliveryRate', 0):.1f}%")
            
            # Category analysis
            category_stats = {}
            for supplier in suppliers:
                category = supplier.get('category', 'unknown')
                if category not in category_stats:
                    category_stats[category] = {
                        'count': 0,
                        'total_value': Decimal('0'),
                        'avg_rating': 0
                    }
                
                category_stats[category]['count'] += 1
                category_stats[category]['total_value'] += Decimal(str(supplier.get('performance', {}).get('totalValue', 0)))
                category_stats[category]['avg_rating'] += float(supplier.get('performance', {}).get('rating', 0))
            
            print(f"\n📂 SUPPLIERS BY CATEGORY:")
            print("-" * 60)
            
            for category, stats in category_stats.items():
                avg_rating = stats['avg_rating'] / stats['count'] if stats['count'] > 0 else 0
                print(f"📂 {category.replace('_', ' ').title()}:")
                print(f"   🏪 Suppliers: {stats['count']}")
                print(f"   💰 Total Value: ₹{stats['total_value']:,.2f}")
                print(f"   ⭐ Avg Rating: {avg_rating:.2f}/5.0")
                print()
            
            # Payment analysis
            print(f"💳 PAYMENT ANALYSIS:")
            print("-" * 60)
            
            try:
                payment_response = self.procurement_table.query(
                    IndexName='TypeIndex',
                    KeyConditionExpression='documentType = :doc_type',
                    ExpressionAttributeValues={':doc_type': 'payment'}
                )
                
                payments = payment_response.get('Items', [])
                
                if payments:
                    total_payments = len(payments)
                    completed_payments = len([p for p in payments if p.get('status') == 'completed'])
                    pending_payments = len([p for p in payments if p.get('status') == 'pending'])
                    
                    total_paid = sum(Decimal(str(p.get('amount', 0))) for p in payments if p.get('status') == 'completed')
                    total_pending = sum(Decimal(str(p.get('amount', 0))) for p in payments if p.get('status') == 'pending')
                    
                    print(f"💳 Total Payments: {total_payments:,}")
                    print(f"✅ Completed: {completed_payments:,} (₹{total_paid:,.2f})")
                    print(f"⏳ Pending: {pending_payments:,} (₹{total_pending:,.2f})")
                    
                    if total_payments > 0:
                        completion_rate = (completed_payments / total_payments) * 100
                        print(f"📊 Payment Completion Rate: {completion_rate:.1f}%")
                else:
                    print("💳 No payment records found")
                    
            except Exception as e:
                print(f"❌ Error loading payment data: {str(e)}")
                
        except Exception as e:
            self.print_error(f"Failed to load supplier analytics: {str(e)}")

    def log_audit_event(self, action: str, resource_type: str, resource_id: str, details: str):
        """Log audit events"""
        try:
            audit_id = str(uuid.uuid4())
            
            audit_event = {
                'entityType': 'audit_log',
                'entityID': audit_id,
                'userID': self.current_user['userID'],
                'action': action,
                'resourceType': resource_type,
                'resourceID': resource_id,
                'oldValues': {},
                'newValues': {},
                'ipAddress': '127.0.0.1',
                'userAgent': 'Aurora Spark Supplier Portal',
                'details': details,
                'status': 'completed',
                'priority': 'normal',
                'createdAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.system_table.put_item(Item=audit_event)
            
        except Exception as e:
            self.print_error(f"Failed to log audit event: {str(e)}")

    def main_menu(self):
        """Main menu for Supplier Portal"""
        while True:
            self.clear_screen()
            self.print_header("SUPPLIER PORTAL MAIN MENU")
            
            if self.current_user:
                role_name = self.current_user.get('primaryRole', 'supplier_manager').replace('_', ' ').title()
                print(f"👤 Logged in as: {self.current_user['firstName']} {self.current_user['lastName']}")
                print(f"📧 Email: {self.current_user['email']}")
                print(f"🔑 Role: {role_name}")
                print(f"🏪 Department: Supplier Management")
                print()
            
            print("🏪 E-COMMERCE - SUPPLIER PORTAL")
            print("Complete Supplier Management & Procurement Operations")
            print()
            print("📊 MAIN MENU OPTIONS:")
            print("-" * 70)
            print("1. 📈 Supplier Dashboard")
            print("2. 🏪 Supplier Management")
            print("3. 📋 Procurement Management")
            print("4. 💰 Billing & Payments")
            print("5. 📊 Supplier Analytics")
            print("6. 📄 Reports & Export")
            print("7. ⚙️  Settings")
            print("0. 🚪 Logout")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                self.logout()
                break
            elif choice == '1':
                self.display_supplier_dashboard()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.supplier_management()
            elif choice == '3':
                self.procurement_management()
            elif choice == '4':
                self.billing_management()
            elif choice == '5':
                self.supplier_analytics()
                input("\nPress Enter to continue...")
            elif choice == '6':
                self.reports_export()
            elif choice == '7':
                self.supplier_settings()
            else:
                self.print_error("Invalid choice. Please try again.")
                input("Press Enter to continue...")

    # Placeholder methods for remaining functionality
    def edit_supplier_details(self):
        self.print_info("Edit supplier details - Coming soon...")

    def supplier_performance(self):
        self.print_info("Supplier performance tracking - Coming soon...")

    def supplier_reviews(self):
        self.print_info("Supplier reviews management - Coming soon...")

    def supplier_categories(self):
        self.print_info("Supplier categories - Coming soon...")

    def supplier_approvals(self):
        self.print_info("Supplier approvals - Coming soon...")

    def supplier_status_management(self):
        self.print_info("Supplier status management - Coming soon...")

    def edit_purchase_order(self):
        self.print_info("Edit purchase order - Coming soon...")

    def receive_goods(self):
        self.print_info("Receive goods - Coming soon...")

    def po_analytics(self):
        self.print_info("PO analytics - Coming soon...")

    def search_purchase_orders(self):
        self.print_info("Search purchase orders - Coming soon...")

    def procurement_trends(self):
        self.print_info("Procurement trends - Coming soon...")

    def overdue_orders(self):
        self.print_info("Overdue orders - Coming soon...")

    def create_new_invoice(self):
        self.print_info("Create new invoice - Coming soon...")

    def process_payments(self):
        self.print_info("Process payments - Coming soon...")

    def payment_reports(self):
        self.print_info("Payment reports - Coming soon...")

    def outstanding_payments(self):
        self.print_info("Outstanding payments - Coming soon...")

    def payment_analytics(self):
        self.print_info("Payment analytics - Coming soon...")

    def payment_methods(self):
        self.print_info("Payment methods - Coming soon...")

    def search_invoices(self):
        self.print_info("Search invoices - Coming soon...")

    def reports_export(self):
        self.print_info("Reports & export - Coming soon...")

    def supplier_settings(self):
        self.print_info("Supplier settings - Coming soon...")

    def logout(self):
        """Logout current user"""
        self.print_success("Logged out successfully")
        print("👋 Thank you for using E-commerce Supplier Portal!")
        self.current_user = None

    def run(self):
        """Main application entry point"""
        self.clear_screen()
        self.print_header("AUTHENTICATION")
        
        print("🏪 Welcome to E-commerce Supplier Portal")
        print("Complete Supplier Management & Procurement Operations")
        print()
        print("🔐 Please authenticate to access the system")
        print("⚠️  Supplier management credentials required")
        print()
        print("🔑 DEFAULT TEST CREDENTIALS:")
        print("   📧 Email: supplier@promodeagro.com")
        print("   🔒 Password: password123")
        print("   📧 Email: admin@promodeagro.com (Super Admin)")
        print("   🔒 Password: password123")
        print()
        print("⚠️  Note: Change default credentials in production!")
        print()
        
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            print(f"Login attempt {attempts + 1}/{max_attempts}")
            email = input("📧 Email: ").strip()
            password = getpass.getpass("🔒 Password: ")
            
            if self.authenticate_user(email, password):
                print("\n✅ Authentication successful!")
                import time
                time.sleep(1)  # Brief pause
                self.main_menu()
                break
            else:
                attempts += 1
                remaining = max_attempts - attempts
                if remaining > 0:
                    self.print_error(f"Authentication failed. {remaining} attempts remaining.")
                    print()
                else:
                    self.print_error("Maximum authentication attempts exceeded.")
                    print()


if __name__ == "__main__":
    try:
        print("🏪 Starting E-commerce Supplier Portal...")
        print("=" * 60)
        
        portal = SupplierPortal()
        portal.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 Supplier Portal terminated by user")
        print("Thank you for using E-commerce Store!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error in Supplier Portal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
