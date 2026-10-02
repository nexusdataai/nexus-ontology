#!/usr/bin/env python3
# warehouse_manager_portal.py
"""
E-commerce - Warehouse Manager Portal
Combined functionality: Warehouse Manager + Logistics Manager + Inventory Staff
Complete warehouse operations, inventory management, logistics coordination, and staff management
"""

import boto3
import sys
import getpass
import os
import json
import uuid
import hashlib
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional


class WarehouseManagerPortal:
    """E-commerce Warehouse Manager Portal - Combined Operations Management"""
    
    def __init__(self):
        self.region_name = 'ap-south-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Aurora Spark Theme Optimized Tables
        self.users_table = self.dynamodb.Table('AuroraSparkTheme-Users')
        self.products_table = self.dynamodb.Table('AuroraSparkTheme-Products')
        self.inventory_table = self.dynamodb.Table('AuroraSparkTheme-Inventory')
        self.orders_table = self.dynamodb.Table('AuroraSparkTheme-Orders')
        self.suppliers_table = self.dynamodb.Table('AuroraSparkTheme-Suppliers')
        self.procurement_table = self.dynamodb.Table('AuroraSparkTheme-Procurement')
        self.logistics_table = self.dynamodb.Table('AuroraSparkTheme-Logistics')
        self.staff_table = self.dynamodb.Table('AuroraSparkTheme-Staff')
        self.quality_table = self.dynamodb.Table('AuroraSparkTheme-Quality')
        self.delivery_table = self.dynamodb.Table('AuroraSparkTheme-Delivery')
        self.analytics_table = self.dynamodb.Table('AuroraSparkTheme-Analytics')
        self.system_table = self.dynamodb.Table('AuroraSparkTheme-System')
        
        self.current_user = None
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 100)
        print(f"🏭 [E-COMMERCE - WAREHOUSE MANAGER] {title}")
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
        """Authenticate warehouse manager (includes warehouse, logistics, inventory roles)"""
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
            
            # Check if user has warehouse manager, logistics manager, or inventory staff role
            user_roles = user.get('roles', [])
            allowed_roles = ['warehouse_manager', 'logistics_manager', 'inventory_staff', 'super_admin']
            
            if not any(role in user_roles for role in allowed_roles):
                self.print_error("Access denied. Warehouse operations role required.")
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
            
            role_name = user.get('primaryRole', 'warehouse_operations').replace('_', ' ').title()
            self.print_success(f"Welcome, {user['firstName']} {user['lastName']} ({role_name})!")
            return True
            
        except Exception as e:
            self.print_error(f"Authentication failed: {str(e)}")
            return False

    def display_warehouse_dashboard(self):
        """Display comprehensive warehouse operations dashboard"""
        self.print_header("WAREHOUSE OPERATIONS DASHBOARD")
        
        try:
            # Inventory Overview
            print("📦 INVENTORY OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get products summary
                products_response = self.products_table.scan()
                products = products_response.get('Items', [])
                
                total_products = len(products)
                active_products = len([p for p in products if p.get('status') == 'active'])
                products_with_variants = len([p for p in products if p.get('hasVariants')])
                
                print(f"🏷️  Total Products: {total_products:,}")
                print(f"✅ Active Products: {active_products:,}")
                print(f"🔄 Products with Variants: {products_with_variants:,}")
                
                # Calculate total inventory value
                total_inventory_value = Decimal('0')
                for product in products:
                    price = Decimal(str(product.get('price', 0)))
                    stock = product.get('currentStock', 0)
                    total_inventory_value += price * stock
                
                print(f"💰 Total Inventory Value: ₹{total_inventory_value:,.2f}")
                
                # Get inventory data
                inventory_response = self.inventory_table.scan()
                inventory_items = inventory_response.get('Items', [])
                
                total_stock_items = sum(item.get('currentStock', 0) for item in inventory_items)
                low_stock_items = 0
                
                for item in inventory_items:
                    # Get product info to check reorder point
                    product_id = item.get('productID')
                    if product_id:
                        product = next((p for p in products if p.get('productID') == product_id), None)
                        if product:
                            current_stock = item.get('currentStock', 0)
                            reorder_point = product.get('reorderPoint', 0)
                            if current_stock <= reorder_point:
                                low_stock_items += 1
                
                print(f"📊 Total Stock Units: {total_stock_items:,}")
                print(f"🔴 Low Stock Alerts: {low_stock_items:,}")
                
            except Exception as e:
                print(f"❌ Error loading inventory data: {str(e)}")
            
            # Staff Overview
            print(f"\n👥 STAFF OVERVIEW:")
            print("-" * 60)
            
            try:
                staff_response = self.staff_table.scan()
                staff_members = staff_response.get('Items', [])
                
                total_staff = len(staff_members)
                active_staff = len([s for s in staff_members if s.get('status') == 'active'])
                on_duty_staff = len([s for s in staff_members if s.get('status') in ['active', 'on_break']])
                
                print(f"👥 Total Staff: {total_staff:,}")
                print(f"✅ Active Staff: {active_staff:,}")
                print(f"🟢 Currently On Duty: {on_duty_staff:,}")
                
                # Staff by department
                departments = {}
                for staff in staff_members:
                    dept = staff.get('jobInfo', {}).get('department', 'unknown')
                    departments[dept] = departments.get(dept, 0) + 1
                
                print(f"\n📊 Staff by Department:")
                dept_emojis = {
                    'warehouse': '🏭',
                    'logistics': '🚛',
                    'quality_control': '🔍',
                    'receiving': '📥',
                    'packing': '📦',
                    'dispatch': '🚚'
                }
                
                for dept, count in departments.items():
                    emoji = dept_emojis.get(dept, '👤')
                    print(f"   {emoji} {dept.replace('_', ' ').title()}: {count}")
                
            except Exception as e:
                print(f"❌ Error loading staff data: {str(e)}")
            
            # Logistics Overview
            print(f"\n🚛 LOGISTICS OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get vehicles
                logistics_response = self.logistics_table.query(
                    IndexName='TypeIndex',
                    KeyConditionExpression='entityType = :entity_type',
                    ExpressionAttributeValues={':entity_type': 'vehicle'}
                )
                
                vehicles = logistics_response.get('Items', [])
                total_vehicles = len(vehicles)
                active_vehicles = len([v for v in vehicles if v.get('status') == 'active'])
                maintenance_vehicles = len([v for v in vehicles if v.get('status') == 'maintenance'])
                
                print(f"🚛 Total Vehicles: {total_vehicles:,}")
                print(f"✅ Active Vehicles: {active_vehicles:,}")
                print(f"🔧 In Maintenance: {maintenance_vehicles:,}")
                
                # Get today's routes
                today = datetime.now(timezone.utc).date().isoformat()
                routes_response = self.logistics_table.query(
                    IndexName='DateIndex',
                    KeyConditionExpression='operationDate = :today AND entityType = :entity_type',
                    ExpressionAttributeValues={
                        ':today': today,
                        ':entity_type': 'route'
                    }
                )
                
                todays_routes = routes_response.get('Items', [])
                completed_routes = len([r for r in todays_routes if r.get('status') == 'completed'])
                in_progress_routes = len([r for r in todays_routes if r.get('status') == 'in_progress'])
                
                print(f"\n📍 Today's Routes: {len(todays_routes):,}")
                print(f"✅ Completed: {completed_routes:,}")
                print(f"🔄 In Progress: {in_progress_routes:,}")
                
            except Exception as e:
                print(f"❌ Error loading logistics data: {str(e)}")
            
            # Orders Overview
            print(f"\n📋 ORDERS OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get today's orders
                today = datetime.now(timezone.utc).date().isoformat()
                orders_response = self.orders_table.query(
                    IndexName='DeliveryDateIndex',
                    KeyConditionExpression='deliveryDate = :today',
                    ExpressionAttributeValues={':today': today}
                )
                
                todays_orders = orders_response.get('Items', [])
                
                if todays_orders:
                    status_counts = {}
                    total_value = Decimal('0')
                    
                    for order in todays_orders:
                        status = order.get('status', 'unknown')
                        status_counts[status] = status_counts.get(status, 0) + 1
                        
                        order_summary = order.get('orderSummary', {})
                        total_amount = order_summary.get('totalAmount', 0)
                        if isinstance(total_amount, (int, float, Decimal)):
                            total_value += Decimal(str(total_amount))
                    
                    print(f"📦 Today's Orders: {len(todays_orders):,}")
                    print(f"💰 Total Value: ₹{total_value:,.2f}")
                    
                    print(f"\n📊 Orders by Status:")
                    status_emojis = {
                        'pending': '⏳',
                        'confirmed': '✅',
                        'packed': '📦',
                        'out_for_delivery': '🚚',
                        'delivered': '✅',
                        'cancelled': '❌'
                    }
                    
                    for status, count in status_counts.items():
                        emoji = status_emojis.get(status, '❓')
                        print(f"   {emoji} {status.replace('_', ' ').title()}: {count}")
                else:
                    print("📦 No orders scheduled for today")
                
            except Exception as e:
                print(f"❌ Error loading orders data: {str(e)}")
            
            # Quality Overview
            print(f"\n🔍 QUALITY OVERVIEW:")
            print("-" * 60)
            
            try:
                # Get quality checks (without date filter since checkDate is primary key)
                quality_response = self.quality_table.query(
                    IndexName='GradeIndex',
                    KeyConditionExpression='overallGrade = :grade',
                    ExpressionAttributeValues={
                        ':grade': 'excellent'
                    }
                )
                
                quality_checks = quality_response.get('Items', [])
                
                if quality_checks:
                    passed_checks = len([q for q in quality_checks if q.get('passed')])
                    pass_rate = (passed_checks / len(quality_checks)) * 100 if quality_checks else 0
                    
                    print(f"🔍 Today's Quality Checks: {len(quality_checks):,}")
                    print(f"✅ Passed Checks: {passed_checks:,}")
                    print(f"📊 Pass Rate: {pass_rate:.1f}%")
                else:
                    print("🔍 No quality checks performed today")
                
            except Exception as e:
                print(f"❌ Error loading quality data: {str(e)}")
                
        except Exception as e:
            self.print_error(f"Failed to load dashboard: {str(e)}")

    def inventory_management(self):
        """Comprehensive inventory management"""
        while True:
            self.print_header("INVENTORY MANAGEMENT")
            print("📦 INVENTORY MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 📋 View All Products")
            print("2. ➕ Add New Product")
            print("3. 🔄 Manage Product Variants")
            print("4. 📊 Stock Levels & Movements")
            print("5. 📥 Receive Stock")
            print("6. ⚖️  Stock Adjustments")
            print("7. 🔄 Stock Transfers")
            print("8. 📈 Inventory Analytics")
            print("9. 🔴 Low Stock Alerts")
            print("10. 🗂️  Product Categories")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_products()
            elif choice == '2':
                self.add_new_product()
            elif choice == '3':
                self.manage_product_variants()
            elif choice == '4':
                self.stock_levels_movements()
            elif choice == '5':
                self.receive_stock()
            elif choice == '6':
                self.stock_adjustments()
            elif choice == '7':
                self.stock_transfers()
            elif choice == '8':
                self.inventory_analytics()
            elif choice == '9':
                self.low_stock_alerts()
            elif choice == '10':
                self.product_categories()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_products(self):
        """View all products with variants"""
        try:
            print("\n📦 PRODUCT CATALOG")
            print("=" * 80)
            
            response = self.products_table.scan()
            products = response.get('Items', [])
            
            if not products:
                self.print_info("No products found")
                return
            
            for i, product in enumerate(products, 1):
                status_emoji = "✅" if product.get('status') == 'active' else "❌"
                quality_emoji = self.get_quality_emoji(product.get('qualityGrade', 'good'))
                
                print(f"{i}. {status_emoji} {product.get('name', 'Unknown Product')}")
                print(f"   🏷️  Code: {product.get('productCode', 'N/A')}")
                print(f"   📂 Category: {product.get('category', 'N/A')}")
                print(f"   💰 Price: ₹{product.get('price', 0):.2f} per {product.get('unit', 'unit')}")
                print(f"   {quality_emoji} Quality: {product.get('qualityGrade', 'N/A').title()}")
                print(f"   📊 Stock: {product.get('currentStock', 0):,} {product.get('unit', 'units')}")
                
                if product.get('hasVariants'):
                    variants = product.get('variants', [])
                    print(f"   🔄 Variants: {len(variants)} available")
                    for variant in variants[:3]:  # Show first 3 variants
                        print(f"      • {variant.get('variantName', 'Unknown')} (SKU: {variant.get('sku', 'N/A')})")
                    if len(variants) > 3:
                        print(f"      • ... and {len(variants) - 3} more variants")
                
                if product.get('perishable'):
                    print(f"   🕒 Shelf Life: {product.get('shelfLifeDays', 'N/A')} days")
                    storage = product.get('storageRequirements', {})
                    temp_min = storage.get('temperatureMin', 0)
                    temp_max = storage.get('temperatureMax', 0)
                    print(f"   🌡️  Storage: {temp_min}°C - {temp_max}°C")
                
                print("-" * 80)
                
        except Exception as e:
            self.print_error(f"Failed to load products: {str(e)}")

    def get_quality_emoji(self, grade: str) -> str:
        """Get emoji for quality grade"""
        quality_emojis = {
            'excellent': '🌟',
            'very-good': '⭐',
            'good': '✅',
            'fair': '⚠️',
            'poor': '❌'
        }
        return quality_emojis.get(grade.lower(), '❓')

    def add_new_product(self):
        """Add a new product with variant support"""
        try:
            print("\n➕ ADD NEW PRODUCT")
            print("=" * 50)
            
            # Basic product information
            product_code = input("🏷️  Product Code: ").strip().upper()
            if not product_code:
                self.print_error("Product code is required")
                return
            
            # Check if product code already exists
            existing_check = self.products_table.query(
                IndexName='CodeIndex',
                KeyConditionExpression='productCode = :code',
                ExpressionAttributeValues={':code': product_code}
            )
            
            if existing_check.get('Items'):
                self.print_error("Product code already exists")
                return
            
            name = input("📦 Product Name: ").strip()
            description = input("📝 Description: ").strip()
            category = input("📂 Category: ").strip()
            unit = input("📏 Unit (kg, pieces, liters, etc.): ").strip()
            price = input("💰 Selling Price: ").strip()
            cost_price = input("💵 Cost Price: ").strip()
            min_stock = input("📊 Minimum Stock Level: ").strip()
            reorder_point = input("🔄 Reorder Point: ").strip()
            
            if not all([name, category, unit, price, cost_price]):
                self.print_error("Name, category, unit, price, and cost price are required")
                return
            
            # Quality and storage info
            print("\n🌟 Quality Grade:")
            print("1. Excellent")
            print("2. Very Good") 
            print("3. Good")
            print("4. Fair")
            print("5. Poor")
            quality_choice = input("Select quality grade (1-5): ").strip()
            
            quality_grades = {
                '1': 'excellent',
                '2': 'very-good',
                '3': 'good', 
                '4': 'fair',
                '5': 'poor'
            }
            quality_grade = quality_grades.get(quality_choice, 'good')
            
            is_perishable = input("🕒 Is perishable? (y/n): ").strip().lower() == 'y'
            shelf_life = None
            temp_min = None
            temp_max = None
            
            if is_perishable:
                shelf_life = input("📅 Shelf life (days): ").strip()
                temp_min = input("🌡️  Min storage temperature (°C): ").strip()
                temp_max = input("🌡️  Max storage temperature (°C): ").strip()
            
            # Variant support
            has_variants = input("🔄 Does this product have variants? (y/n): ").strip().lower() == 'y'
            variants = []
            
            if has_variants:
                print("\n🔄 PRODUCT VARIANTS:")
                variant_count = input("How many variants to add? ").strip()
                
                if variant_count.isdigit() and int(variant_count) > 0:
                    for i in range(int(variant_count)):
                        print(f"\nVariant {i+1}:")
                        variant_name = input("  Variant Name: ").strip()
                        variant_type = input("  Variant Type (size/color/weight/flavor): ").strip()
                        variant_value = input("  Variant Value: ").strip()
                        price_adj = input("  Price Adjustment (±amount): ").strip()
                        
                        if variant_name and variant_type and variant_value:
                            variant_id = str(uuid.uuid4())
                            variant_sku = f"{product_code}-{variant_value.upper()[:3]}"
                            
                            variant = {
                                'variantID': variant_id,
                                'variantName': variant_name,
                                'variantType': variant_type,
                                'variantValue': variant_value,
                                'sku': variant_sku,
                                'barcode': f"VAR{uuid.uuid4().hex[:10].upper()}",
                                'priceAdjustment': Decimal(price_adj) if price_adj else Decimal('0.00'),
                                'attributes': {},
                                'isActive': True
                            }
                            variants.append(variant)
            
            # Create product
            product_id = str(uuid.uuid4())
            
            product_data = {
                'productID': product_id,
                'category': category,
                'productCode': product_code,
                'name': name,
                'description': description,
                'unit': unit,
                'price': Decimal(price),
                'costPrice': Decimal(cost_price),
                'currentStock': 0,
                'minStockLevel': int(min_stock) if min_stock else 0,
                'maxStockLevel': int(min_stock) * 10 if min_stock else 1000,
                'reorderPoint': int(reorder_point) if reorder_point else 0,
                'status': 'active',
                'qualityGrade': quality_grade,
                'perishable': is_perishable,
                'shelfLifeDays': int(shelf_life) if shelf_life else None,
                'hasVariants': has_variants,
                'variants': variants,
                'storageRequirements': {
                    'temperatureMin': Decimal(temp_min) if temp_min else None,
                    'temperatureMax': Decimal(temp_max) if temp_max else None,
                    'storageType': 'cold_storage' if is_perishable else 'ambient'
                },
                'categoryInfo': {
                    'categoryID': f"cat-{category.lower()}",
                    'categoryName': category.title(),
                    'categoryColor': '#4CAF50'
                },
                'supplierID': None,
                'isB2cAvailable': True,
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.products_table.put_item(Item=product_data)
            
            # Log the action
            self.log_audit_event('CREATE_PRODUCT', 'Product', product_id, 
                               f"Created product: {name} with {len(variants)} variants")
            
            self.print_success(f"Product '{name}' created successfully!")
            print(f"🔑 Product ID: {product_id}")
            print(f"🏷️  Product Code: {product_code}")
            if has_variants:
                print(f"🔄 Variants Created: {len(variants)}")
                for variant in variants:
                    print(f"   • {variant['variantName']} (SKU: {variant['sku']})")
            
        except Exception as e:
            self.print_error(f"Failed to add product: {str(e)}")

    def logistics_management(self):
        """Logistics and fleet management"""
        while True:
            self.print_header("LOGISTICS MANAGEMENT")
            print("🚛 LOGISTICS MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 🚛 Fleet Management")
            print("2. 📍 Route Planning")
            print("3. 📋 Create Runsheets")
            print("4. 👤 Assign Runsheets to Riders")
            print("5. 📱 Delivery Tracking")
            print("6. 📊 Route Optimization")
            print("7. 👥 Driver Management")
            print("8. ⛽ Fuel Management")
            print("9. 🔧 Vehicle Maintenance")
            print("10. 📈 Logistics Analytics")
            print("11. 🕒 Delivery Slots Management")
            print("12. 🚨 Emergency Operations")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.fleet_management()
            elif choice == '2':
                self.route_planning()
            elif choice == '3':
                self.create_runsheets()
            elif choice == '4':
                self.assign_runsheets()
            elif choice == '5':
                self.delivery_tracking()
            elif choice == '6':
                self.route_optimization()
            elif choice == '7':
                self.driver_management()
            elif choice == '8':
                self.fuel_management()
            elif choice == '9':
                self.vehicle_maintenance()
            elif choice == '10':
                self.logistics_analytics()
            elif choice == '11':
                self.delivery_slots_management()
            elif choice == '12':
                self.emergency_operations()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def fleet_management(self):
        """Fleet vehicle management"""
        try:
            print("\n🚛 FLEET MANAGEMENT")
            print("=" * 60)
            
            # Get all vehicles
            response = self.logistics_table.query(
                IndexName='TypeIndex',
                KeyConditionExpression='entityType = :entity_type',
                ExpressionAttributeValues={':entity_type': 'vehicle'}
            )
            
            vehicles = response.get('Items', [])
            
            if not vehicles:
                self.print_info("No vehicles found in fleet")
                return
            
            print(f"🚛 FLEET VEHICLES ({len(vehicles)} total):")
            print("-" * 80)
            
            for vehicle in vehicles:
                vehicle_info = vehicle.get('vehicleInfo', {})
                status_emoji = {
                    'active': '✅',
                    'maintenance': '🔧',
                    'inactive': '❌'
                }.get(vehicle.get('status', 'inactive'), '❓')
                
                fuel_emoji = {
                    'petrol': '⛽',
                    'diesel': '🛢️',
                    'electric': '🔋',
                    'cng': '💨'
                }.get(vehicle_info.get('fuelType', 'petrol'), '⛽')
                
                print(f"{status_emoji} {vehicle_info.get('vehicleNumber', 'Unknown')}")
                print(f"   🚛 Type: {vehicle_info.get('vehicleType', 'N/A').title()}")
                print(f"   🏭 Model: {vehicle_info.get('model', 'N/A')}")
                print(f"   {fuel_emoji} Fuel: {vehicle_info.get('fuelType', 'N/A').title()}")
                print(f"   📦 Capacity: {vehicle_info.get('capacityKg', 0):,.0f} kg")
                print(f"   📊 Status: {vehicle.get('status', 'N/A').title()}")
                
                # Driver assignment
                assignment_info = vehicle.get('assignmentInfo', {})
                if assignment_info.get('driverID'):
                    print(f"   👤 Driver: {assignment_info.get('driverID', 'N/A')}")
                    print(f"   🏠 Home Base: {assignment_info.get('homeBase', 'N/A')}")
                
                # Maintenance info
                maintenance = vehicle.get('maintenance', {})
                if maintenance.get('lastMaintenanceDate'):
                    print(f"   🔧 Last Maintenance: {maintenance.get('lastMaintenanceDate')}")
                if maintenance.get('nextMaintenanceDate'):
                    print(f"   📅 Next Maintenance: {maintenance.get('nextMaintenanceDate')}")
                
                print("-" * 80)
                
        except Exception as e:
            self.print_error(f"Failed to load fleet data: {str(e)}")

    def staff_management(self):
        """Staff management and coordination"""
        while True:
            self.print_header("STAFF MANAGEMENT")
            print("👥 STAFF MANAGEMENT OPTIONS:")
            print("-" * 60)
            print("1. 📋 View All Staff")
            print("2. ➕ Add New Staff Member")
            print("3. 📊 Staff Performance")
            print("4. 📅 Attendance Management")
            print("5. 📝 Task Assignment")
            print("6. 🎯 Performance Reviews")
            print("7. 📈 Staff Analytics")
            print("8. 🔄 Shift Management")
            print("9. 👥 Department Overview")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_staff()
            elif choice == '2':
                self.add_staff_member()
            elif choice == '3':
                self.staff_performance()
            elif choice == '4':
                self.attendance_management()
            elif choice == '5':
                self.task_assignment()
            elif choice == '6':
                self.performance_reviews()
            elif choice == '7':
                self.staff_analytics()
            elif choice == '8':
                self.shift_management()
            elif choice == '9':
                self.department_overview()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_staff(self):
        """View all staff members"""
        try:
            print("\n👥 STAFF DIRECTORY")
            print("=" * 80)
            
            response = self.staff_table.scan()
            staff_members = response.get('Items', [])
            
            if not staff_members:
                self.print_info("No staff members found")
                return
            
            # Group by department
            staff_by_dept = {}
            for staff in staff_members:
                job_info = staff.get('jobInfo', {})
                dept = job_info.get('department', 'unknown')
                if dept not in staff_by_dept:
                    staff_by_dept[dept] = []
                staff_by_dept[dept].append(staff)
            
            dept_emojis = {
                'warehouse': '🏭',
                'logistics': '🚛',
                'quality_control': '🔍',
                'receiving': '📥',
                'packing': '📦',
                'dispatch': '🚚',
                'administration': '🏢'
            }
            
            for dept, dept_staff in staff_by_dept.items():
                emoji = dept_emojis.get(dept, '👤')
                print(f"\n{emoji} {dept.upper().replace('_', ' ')} DEPARTMENT ({len(dept_staff)} staff):")
                print("-" * 60)
                
                for staff in dept_staff:
                    personal_info = staff.get('personalInfo', {})
                    job_info = staff.get('jobInfo', {})
                    performance = staff.get('performance', {})
                    
                    status_emoji = {
                        'active': '✅',
                        'on_break': '⏸️',
                        'off_duty': '🔴',
                        'on_leave': '🏖️',
                        'inactive': '❌'
                    }.get(staff.get('status', 'inactive'), '❓')
                    
                    name = f"{personal_info.get('firstName', '')} {personal_info.get('lastName', '')}"
                    
                    print(f"{status_emoji} {name}")
                    print(f"   🆔 Employee ID: {staff.get('employeeID', 'N/A')}")
                    print(f"   💼 Position: {job_info.get('position', 'N/A')}")
                    print(f"   🕐 Shift: {job_info.get('shift', 'N/A').title()}")
                    print(f"   📊 Status: {staff.get('status', 'N/A').title()}")
                    print(f"   ⭐ Performance: {performance.get('score', 0):.1f}/5.0")
                    print(f"   📞 Phone: {personal_info.get('phone', 'N/A')}")
                    print(f"   📧 Email: {personal_info.get('email', 'N/A')}")
                    
                    # Shift timing
                    shift_timing = job_info.get('shiftTiming', {})
                    if shift_timing:
                        print(f"   🕐 Timing: {shift_timing.get('startTime', 'N/A')} - {shift_timing.get('endTime', 'N/A')}")
                    
                    print("-" * 60)
                    
        except Exception as e:
            self.print_error(f"Failed to load staff data: {str(e)}")

    def quality_control(self):
        """Quality control and monitoring"""
        while True:
            self.print_header("QUALITY CONTROL")
            print("🔍 QUALITY CONTROL OPTIONS:")
            print("-" * 60)
            print("1. 📋 View Quality Checks")
            print("2. ✅ Perform Quality Check")
            print("3. 📊 Quality Reports")
            print("4. 🌡️  Temperature Monitoring")
            print("5. 🗑️  Waste Management")
            print("6. 📈 Quality Analytics")
            print("7. ⚙️  Quality Standards")
            print("8. 🚨 Quality Alerts")
            print("0. ⬅️  Back to Main Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_quality_checks()
            elif choice == '2':
                self.perform_quality_check()
            elif choice == '3':
                self.quality_reports()
            elif choice == '4':
                self.temperature_monitoring()
            elif choice == '5':
                self.waste_management()
            elif choice == '6':
                self.quality_analytics()
            elif choice == '7':
                self.quality_standards()
            elif choice == '8':
                self.quality_alerts()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_quality_checks(self):
        """View recent quality checks"""
        try:
            print("\n🔍 QUALITY CHECKS HISTORY")
            print("=" * 80)
            
            response = self.quality_table.scan(Limit=20)
            checks = response.get('Items', [])
            
            if not checks:
                self.print_info("No quality checks found")
                return
            
            print(f"🔍 RECENT QUALITY CHECKS ({len(checks)} shown):")
            print("-" * 80)
            
            for check in sorted(checks, key=lambda x: x.get('checkDate', ''), reverse=True):
                status_emoji = "✅" if check.get('passed') else "❌"
                grade_emoji = self.get_quality_emoji(check.get('overallGrade', 'good'))
                
                print(f"{status_emoji} Check #{check.get('checkNumber', 'N/A')}")
                print(f"   📦 Product ID: {check.get('productID', 'N/A')}")
                if check.get('variantID'):
                    print(f"   🔄 Variant ID: {check.get('variantID', 'N/A')}")
                print(f"   🔍 Type: {check.get('checkType', 'N/A').title()}")
                print(f"   {grade_emoji} Grade: {check.get('overallGrade', 'N/A').title()}")
                print(f"   📊 Score: {check.get('overallScore', 0):.1f}/10.0")
                print(f"   🌡️  Temperature: {check.get('temperatureAtCheck', 0)}°C")
                print(f"   📅 Date: {check.get('checkDate', 'N/A')}")
                print(f"   👤 Inspector: {check.get('inspectorID', 'N/A')}")
                
                if check.get('notes'):
                    print(f"   📝 Notes: {check['notes']}")
                
                if not check.get('passed') and check.get('rejectionReason'):
                    print(f"   ❌ Rejection: {check['rejectionReason']}")
                
                print("-" * 80)
                
        except Exception as e:
            self.print_error(f"Failed to load quality checks: {str(e)}")

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
                'userAgent': 'Aurora Spark Warehouse Manager Portal',
                'details': details,
                'status': 'completed',
                'priority': 'normal',
                'createdAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.system_table.put_item(Item=audit_event)
            
        except Exception as e:
            self.print_error(f"Failed to log audit event: {str(e)}")

    def main_menu(self):
        """Main menu for Warehouse Manager Portal"""
        while True:
            self.clear_screen()
            self.print_header("WAREHOUSE MANAGER MAIN MENU")
            
            if self.current_user:
                role_name = self.current_user.get('primaryRole', 'warehouse_operations').replace('_', ' ').title()
                print(f"👤 Logged in as: {self.current_user['firstName']} {self.current_user['lastName']}")
                print(f"📧 Email: {self.current_user['email']}")
                print(f"🔑 Role: {role_name}")
                print(f"🏭 Department: {self.current_user.get('profile', {}).get('department', 'Warehouse')}")
                print()
            
            print("🏭 AURORA SPARK THEME - WAREHOUSE MANAGER PORTAL")
            print("Combined: Warehouse + Logistics + Inventory Operations")
            print()
            print("📊 MAIN MENU OPTIONS:")
            print("-" * 70)
            print("1. 📈 Warehouse Dashboard")
            print("2. 📦 Inventory Management")
            print("3. 🚛 Logistics Management")
            print("4. 👥 Staff Management")
            print("5. 🔍 Quality Control")
            print("6. 📋 Order Processing")
            print("7. 📊 Analytics & Reports")
            print("8. ⚙️  Settings")
            print("0. 🚪 Logout")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                self.logout()
                break
            elif choice == '1':
                self.display_warehouse_dashboard()
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.inventory_management()
            elif choice == '3':
                self.logistics_management()
            elif choice == '4':
                self.staff_management()
            elif choice == '5':
                self.quality_control()
            elif choice == '6':
                self.order_processing()
            elif choice == '7':
                self.analytics_reports()
            elif choice == '8':
                self.warehouse_settings()
            else:
                self.print_error("Invalid choice. Please try again.")
                input("Press Enter to continue...")

    # Placeholder methods for remaining functionality
    def manage_product_variants(self):
        self.print_info("Product variants management - Coming soon...")

    def stock_levels_movements(self):
        """View stock levels and movements"""
        try:
            self.print_header("STOCK LEVELS & MOVEMENTS")
            
            # Get inventory data
            response = self.inventory_table.scan()
            inventory_items = response.get('Items', [])
            
            if not inventory_items:
                self.print_info("No inventory items found")
                return
            
            print(f"📦 CURRENT STOCK LEVELS ({len(inventory_items)} items):")
            print("=" * 80)
            
            # Sort by current stock (lowest first to highlight low stock)
            sorted_items = sorted(inventory_items, key=lambda x: x.get('currentStock', 0))
            
            for item in sorted_items:
                product_name = item.get('productName', 'Unknown Product')
                current_stock = item.get('currentStock', 0)
                available_stock = item.get('availableStock', 0)
                reserved_stock = item.get('reservedStock', 0)
                reorder_level = item.get('reorderLevel', 0)
                
                # Determine stock status
                if current_stock == 0:
                    status = "🔴 OUT OF STOCK"
                elif current_stock <= reorder_level:
                    status = "🟡 LOW STOCK"
                else:
                    status = "🟢 HEALTHY"
                
                print(f"\n📦 {product_name} {status}")
                print(f"   📊 Current Stock: {current_stock:,}")
                print(f"   ✅ Available: {available_stock:,}")
                print(f"   🔒 Reserved: {reserved_stock:,}")
                print(f"   ⚠️  Reorder Level: {reorder_level:,}")
                
                if item.get('batchNumber'):
                    print(f"   🏷️  Batch: {item['batchNumber']}")
                
                if item.get('expiryDate'):
                    print(f"   📅 Expires: {item['expiryDate'][:10]}")
                    
        except Exception as e:
            self.print_error(f"Failed to load stock levels: {str(e)}")

    def receive_stock(self):
        """Receive new stock"""
        try:
            self.print_header("RECEIVE STOCK")
            
            # Get product to receive stock for
            product_id = input("📦 Enter Product ID: ").strip()
            if not product_id:
                self.print_error("Product ID is required")
                return
            
            # Check if product exists
            try:
                product_response = self.products_table.get_item(
                    Key={'productID': product_id, 'category': 'unknown'}  # We need to handle this better
                )
                if 'Item' not in product_response:
                    self.print_error("Product not found")
                    return
                    
                product = product_response['Item']
                print(f"📦 Product: {product.get('name', 'Unknown')}")
                
            except:
                self.print_error("Error finding product")
                return
            
            # Get quantity to receive
            try:
                quantity = int(input("📊 Quantity to receive: ").strip())
                if quantity <= 0:
                    self.print_error("Quantity must be positive")
                    return
            except ValueError:
                self.print_error("Invalid quantity")
                return
            
            # Get batch information
            batch_number = input("🏷️  Batch Number (optional): ").strip()
            if not batch_number:
                batch_number = f"BATCH-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            # Update inventory
            from decimal import Decimal
            
            # Find existing inventory record
            inventory_response = self.inventory_table.scan(
                FilterExpression='productID = :pid',
                ExpressionAttributeValues={':pid': product_id}
            )
            
            inventory_items = inventory_response.get('Items', [])
            
            if inventory_items:
                # Update existing inventory
                inventory_item = inventory_items[0]
                current_stock = inventory_item.get('currentStock', 0)
                new_stock = current_stock + quantity
                
                self.inventory_table.update_item(
                    Key={
                        'productID': inventory_item['productID'],
                        'location#batch': inventory_item['location#batch']
                    },
                    UpdateExpression='SET currentStock = :stock, availableStock = availableStock + :qty, batchNumber = :batch, lastUpdated = :updated',
                    ExpressionAttributeValues={
                        ':stock': new_stock,
                        ':qty': quantity,
                        ':batch': batch_number,
                        ':updated': datetime.now(timezone.utc).isoformat()
                    }
                )
                
                self.print_success(f"Stock received successfully!")
                print(f"📦 Product: {product.get('name', 'Unknown')}")
                print(f"📊 Received: {quantity:,} units")
                print(f"📈 New Stock Level: {new_stock:,} units")
                print(f"🏷️  Batch: {batch_number}")
                
            else:
                self.print_error("No existing inventory record found. Please add product to inventory first.")
                
        except Exception as e:
            self.print_error(f"Failed to receive stock: {str(e)}")

    def stock_adjustments(self):
        """Make stock adjustments"""
        try:
            self.print_header("STOCK ADJUSTMENTS")
            
            print("📊 ADJUSTMENT TYPES:")
            print("1. ➕ Increase Stock")
            print("2. ➖ Decrease Stock")
            print("3. 🔄 Set Exact Stock Level")
            print("0. ❌ Cancel")
            
            choice = input("\nSelect adjustment type: ").strip()
            
            if choice == '0':
                return
            
            # Get product
            product_id = input("📦 Enter Product ID: ").strip()
            if not product_id:
                self.print_error("Product ID is required")
                return
            
            # Find inventory record
            inventory_response = self.inventory_table.scan(
                FilterExpression='productID = :pid',
                ExpressionAttributeValues={':pid': product_id}
            )
            
            inventory_items = inventory_response.get('Items', [])
            if not inventory_items:
                self.print_error("Product not found in inventory")
                return
            
            inventory_item = inventory_items[0]
            current_stock = inventory_item.get('currentStock', 0)
            
            print(f"📦 Current Stock: {current_stock:,}")
            
            # Get adjustment amount
            try:
                if choice == '1':  # Increase
                    amount = int(input("➕ Amount to add: ").strip())
                    new_stock = current_stock + amount
                elif choice == '2':  # Decrease
                    amount = int(input("➖ Amount to subtract: ").strip())
                    new_stock = max(0, current_stock - amount)
                elif choice == '3':  # Set exact
                    new_stock = int(input("🔄 New stock level: ").strip())
                    amount = new_stock - current_stock
                else:
                    self.print_error("Invalid choice")
                    return
                    
                if new_stock < 0:
                    self.print_error("Stock cannot be negative")
                    return
                    
            except ValueError:
                self.print_error("Invalid amount")
                return
            
            # Get reason
            reason = input("📝 Reason for adjustment: ").strip()
            if not reason:
                reason = "Manual adjustment"
            
            # Confirm adjustment
            print(f"\n📊 ADJUSTMENT SUMMARY:")
            print(f"📦 Product ID: {product_id}")
            print(f"📈 Current Stock: {current_stock:,}")
            print(f"📊 New Stock: {new_stock:,}")
            print(f"🔄 Change: {amount:+,}")
            print(f"📝 Reason: {reason}")
            
            confirm = input("\n✅ Confirm adjustment? (y/n): ").strip().lower()
            if confirm != 'y':
                self.print_info("Adjustment cancelled")
                return
            
            # Apply adjustment
            self.inventory_table.update_item(
                Key={
                    'productID': inventory_item['productID'],
                    'location#batch': inventory_item['location#batch']
                },
                UpdateExpression='SET currentStock = :stock, availableStock = :available, lastUpdated = :updated',
                ExpressionAttributeValues={
                    ':stock': new_stock,
                    ':available': new_stock - inventory_item.get('reservedStock', 0),
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.print_success("Stock adjustment completed!")
            print(f"📊 New Stock Level: {new_stock:,}")
            
        except Exception as e:
            self.print_error(f"Failed to make stock adjustment: {str(e)}")

    def stock_transfers(self):
        """Transfer stock between locations"""
        try:
            self.print_header("STOCK TRANSFERS")
            
            print("🔄 STOCK TRANSFER BETWEEN LOCATIONS")
            print("=" * 50)
            
            # Get product
            product_id = input("📦 Enter Product ID: ").strip()
            if not product_id:
                self.print_error("Product ID is required")
                return
            
            # Get source and destination
            source_location = input("📍 Source Location (e.g., warehouse-A): ").strip()
            dest_location = input("📍 Destination Location (e.g., warehouse-B): ").strip()
            
            if not source_location or not dest_location:
                self.print_error("Both source and destination locations are required")
                return
            
            if source_location == dest_location:
                self.print_error("Source and destination cannot be the same")
                return
            
            # Get quantity
            try:
                quantity = int(input("📊 Quantity to transfer: ").strip())
                if quantity <= 0:
                    self.print_error("Quantity must be positive")
                    return
            except ValueError:
                self.print_error("Invalid quantity")
                return
            
            # Note: This is a simplified implementation
            # In a real system, you'd need to check source inventory, update both locations, etc.
            
            self.print_success("Stock transfer initiated!")
            print(f"📦 Product: {product_id}")
            print(f"📊 Quantity: {quantity:,}")
            print(f"📍 From: {source_location}")
            print(f"📍 To: {dest_location}")
            print(f"📅 Transfer Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # In a real implementation, you would:
            # 1. Check source location has enough stock
            # 2. Create transfer record
            # 3. Update source location (decrease stock)
            # 4. Update destination location (increase stock)
            # 5. Log the transfer
            
        except Exception as e:
            self.print_error(f"Failed to transfer stock: {str(e)}")

    def inventory_analytics(self):
        """Comprehensive inventory analytics"""
        try:
            self.print_header("INVENTORY ANALYTICS")
            
            # Get inventory data
            response = self.inventory_table.scan()
            inventory_items = response.get('Items', [])
            
            if not inventory_items:
                self.print_info("No inventory data available")
                return
            
            print("📊 INVENTORY ANALYTICS DASHBOARD")
            print("=" * 70)
            
            # Overall statistics
            total_items = len(inventory_items)
            total_stock = sum(item.get('currentStock', 0) for item in inventory_items)
            total_value = sum(float(item.get('totalValue', 0)) for item in inventory_items)
            
            print(f"📦 OVERVIEW:")
            print(f"   📋 Total Items: {total_items:,}")
            print(f"   📊 Total Stock: {total_stock:,} units")
            print(f"   💰 Total Value: ₹{total_value:,.2f}")
            
            # Stock status analysis
            out_of_stock = len([item for item in inventory_items if item.get('currentStock', 0) == 0])
            low_stock = len([item for item in inventory_items if 0 < item.get('currentStock', 0) <= item.get('reorderLevel', 0)])
            healthy_stock = total_items - out_of_stock - low_stock
            
            print(f"\n📊 STOCK STATUS:")
            print(f"   🔴 Out of Stock: {out_of_stock} ({(out_of_stock/total_items*100):.1f}%)")
            print(f"   🟡 Low Stock: {low_stock} ({(low_stock/total_items*100):.1f}%)")
            print(f"   🟢 Healthy Stock: {healthy_stock} ({(healthy_stock/total_items*100):.1f}%)")
            
            # Category analysis
            categories = {}
            for item in inventory_items:
                category = item.get('category', 'unknown')
                if category not in categories:
                    categories[category] = {'items': 0, 'stock': 0, 'value': 0}
                
                categories[category]['items'] += 1
                categories[category]['stock'] += item.get('currentStock', 0)
                categories[category]['value'] += float(item.get('totalValue', 0))
            
            print(f"\n📂 BY CATEGORY:")
            for category, stats in sorted(categories.items(), key=lambda x: x[1]['value'], reverse=True):
                print(f"   📂 {category.title()}:")
                print(f"      📋 Items: {stats['items']}")
                print(f"      📊 Stock: {stats['stock']:,} units")
                print(f"      💰 Value: ₹{stats['value']:,.2f}")
            
            # Top items by value
            print(f"\n💎 TOP ITEMS BY VALUE:")
            sorted_items = sorted(inventory_items, key=lambda x: float(x.get('totalValue', 0)), reverse=True)
            for i, item in enumerate(sorted_items[:5], 1):
                product_name = item.get('productName', 'Unknown')
                stock = item.get('currentStock', 0)
                value = float(item.get('totalValue', 0))
                print(f"   {i}. {product_name}: {stock:,} units (₹{value:,.2f})")
            
        except Exception as e:
            self.print_error(f"Failed to load inventory analytics: {str(e)}")

    def low_stock_alerts(self):
        """Show low stock alerts and recommendations"""
        try:
            self.print_header("LOW STOCK ALERTS")
            
            # Get inventory data
            response = self.inventory_table.scan()
            inventory_items = response.get('Items', [])
            
            if not inventory_items:
                self.print_info("No inventory data available")
                return
            
            # Find low stock and out of stock items
            out_of_stock = []
            low_stock = []
            
            for item in inventory_items:
                current_stock = item.get('currentStock', 0)
                reorder_level = item.get('reorderLevel', 0)
                
                if current_stock == 0:
                    out_of_stock.append(item)
                elif current_stock <= reorder_level:
                    low_stock.append(item)
            
            print("🚨 STOCK ALERTS DASHBOARD")
            print("=" * 60)
            
            if not out_of_stock and not low_stock:
                print("✅ No stock alerts - All items are adequately stocked!")
                return
            
            # Out of stock items
            if out_of_stock:
                print(f"🔴 CRITICAL - OUT OF STOCK ({len(out_of_stock)} items):")
                print("-" * 50)
                for item in sorted(out_of_stock, key=lambda x: x.get('productName', '')):
                    product_name = item.get('productName', 'Unknown')
                    reorder_qty = item.get('reorderQuantity', 100)
                    print(f"   🔴 {product_name}")
                    print(f"      📊 Current: 0 units")
                    print(f"      📦 Suggested Order: {reorder_qty:,} units")
                    print()
            
            # Low stock items
            if low_stock:
                print(f"🟡 WARNING - LOW STOCK ({len(low_stock)} items):")
                print("-" * 50)
                for item in sorted(low_stock, key=lambda x: x.get('currentStock', 0)):
                    product_name = item.get('productName', 'Unknown')
                    current_stock = item.get('currentStock', 0)
                    reorder_level = item.get('reorderLevel', 0)
                    reorder_qty = item.get('reorderQuantity', 100)
                    
                    print(f"   🟡 {product_name}")
                    print(f"      📊 Current: {current_stock:,} units")
                    print(f"      ⚠️  Reorder Level: {reorder_level:,} units")
                    print(f"      📦 Suggested Order: {reorder_qty:,} units")
                    print()
            
            # Summary and recommendations
            total_alerts = len(out_of_stock) + len(low_stock)
            print(f"📊 SUMMARY:")
            print(f"   🚨 Total Alerts: {total_alerts}")
            print(f"   🔴 Critical (Out of Stock): {len(out_of_stock)}")
            print(f"   🟡 Warning (Low Stock): {len(low_stock)}")
            
            if total_alerts > 0:
                print(f"\n💡 RECOMMENDATIONS:")
                print(f"   1. 🚨 Immediately reorder out-of-stock items")
                print(f"   2. 📋 Review reorder levels for frequently low items")
                print(f"   3. 📞 Contact suppliers for urgent deliveries")
                print(f"   4. 📊 Consider increasing safety stock levels")
                
        except Exception as e:
            self.print_error(f"Failed to load low stock alerts: {str(e)}")

    def product_categories(self):
        self.print_info("Product categories - Coming soon...")

    def route_planning(self):
        """Route planning and optimization"""
        try:
            self.print_header("ROUTE PLANNING")
            
            print("🗺️  ROUTE PLANNING DASHBOARD")
            print("=" * 60)
            
            # Get today's orders for route planning
            today = datetime.now(timezone.utc).date().isoformat()
            
            try:
                orders_response = self.orders_table.query(
                    IndexName='DeliveryDateIndex',
                    KeyConditionExpression='deliveryDate = :today',
                    ExpressionAttributeValues={':today': today}
                )
                
                orders = orders_response.get('Items', [])
                
                if not orders:
                    print("📋 No deliveries scheduled for today")
                    return
                
                print(f"📦 DELIVERIES FOR TODAY ({len(orders)} orders):")
                print("-" * 50)
                
                # Group orders by pincode for route optimization
                routes = {}
                for order in orders:
                    pincode = order.get('deliveryPincode', 'unknown')
                    if pincode not in routes:
                        routes[pincode] = []
                    routes[pincode].append(order)
                
                route_num = 1
                for pincode, pincode_orders in sorted(routes.items()):
                    print(f"\n🚛 ROUTE {route_num} - PINCODE {pincode}:")
                    print(f"   📦 Orders: {len(pincode_orders)}")
                    
                    total_value = sum(float(order.get('pricing', {}).get('finalAmount', 0)) for order in pincode_orders)
                    print(f"   💰 Total Value: ₹{total_value:,.2f}")
                    
                    # Show delivery time slots
                    time_slots = set(order.get('deliveryTimeSlot', 'N/A') for order in pincode_orders)
                    print(f"   🕒 Time Slots: {', '.join(time_slots)}")
                    
                    # Show addresses (simplified)
                    addresses = [order.get('deliveryAddress', {}).get('street', 'N/A') for order in pincode_orders]
                    print(f"   📍 Addresses: {len(set(addresses))} unique locations")
                    
                    route_num += 1
                
                print(f"\n📊 ROUTE SUMMARY:")
                print(f"   🚛 Total Routes: {len(routes)}")
                print(f"   📦 Total Orders: {len(orders)}")
                print(f"   📍 Pincodes Covered: {len(routes)}")
                
                # Route optimization suggestions
                print(f"\n💡 OPTIMIZATION SUGGESTIONS:")
                if len(routes) > 5:
                    print("   🔄 Consider consolidating routes for nearby pincodes")
                if any(len(orders) > 20 for orders in routes.values()):
                    print("   📦 Some routes have high order volume - consider splitting")
                print("   🕒 Group orders by time slots for efficient delivery")
                print("   ⛽ Plan fuel stops for long routes")
                
            except Exception as e:
                print(f"❌ Error loading orders: {str(e)}")
                
        except Exception as e:
            self.print_error(f"Failed to load route planning: {str(e)}")

    def create_runsheets(self):
        """Create delivery runsheets for orders"""
        try:
            self.print_header("CREATE DELIVERY RUNSHEETS")
            
            # Get orders ready for delivery
            response = self.orders_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'ready_for_delivery'}
            )
            ready_orders = response.get('Items', [])
            
            if not ready_orders:
                self.print_info("No orders ready for runsheet creation")
                print("💡 Tip: Orders must be packed and verified first")
                input("Press Enter to continue...")
                return
            
            # Group orders by delivery area/pincode for efficient runsheets
            area_groups = {}
            for order in ready_orders:
                pincode = order.get('deliveryPincode', 'Unknown')
                delivery_date = order.get('deliveryDate', datetime.now().date().isoformat())
                time_slot = order.get('deliveryTimeSlot', 'Unknown')
                
                # Create grouping key: pincode + date + time_slot
                group_key = f"{pincode}_{delivery_date}_{time_slot}"
                
                if group_key not in area_groups:
                    area_groups[group_key] = {
                        'pincode': pincode,
                        'delivery_date': delivery_date,
                        'time_slot': time_slot,
                        'orders': []
                    }
                area_groups[group_key]['orders'].append(order)
            
            print(f"📋 Found {len(ready_orders)} orders ready for runsheet creation:")
            print(f"🗂️ Grouped into {len(area_groups)} runsheets by area/date/time:")
            print("-" * 80)
            
            runsheet_preview = []
            for i, (group_key, group_data) in enumerate(area_groups.items(), 1):
                orders = group_data['orders']
                total_value = sum(Decimal(str(order.get('orderSummary', {}).get('totalAmount', 0))) for order in orders)
                
                print(f"\n📋 Runsheet {i}: {group_data['pincode']} - {group_data['delivery_date']}")
                print(f"   🕒 Time Slot: {group_data['time_slot']}")
                print(f"   📦 Orders: {len(orders)}")
                print(f"   💰 Total Value: ₹{total_value:,.2f}")
                print("   📋 Sample Orders:")
                
                for order in orders[:3]:  # Show first 3 orders
                    order_id = order.get('orderID', 'Unknown')[:8]
                    customer_name = order.get('customerInfo', {}).get('name', 'Unknown')
                    items_count = len(order.get('items', []))
                    print(f"      • {order_id}... - {customer_name} ({items_count} items)")
                
                if len(orders) > 3:
                    print(f"      ... and {len(orders) - 3} more orders")
                
                runsheet_preview.append({
                    'group_key': group_key,
                    'group_data': group_data,
                    'total_value': total_value
                })
            
            create_choice = input(f"\nCreate {len(area_groups)} runsheets? (y/N): ").strip().lower()
            
            if create_choice == 'y':
                created_count = 0
                created_runsheets = []
                
                for i, runsheet_info in enumerate(runsheet_preview, 1):
                    try:
                        group_data = runsheet_info['group_data']
                        orders = group_data['orders']
                        
                        # Create runsheet
                        runsheet_id = str(uuid.uuid4())
                        runsheet_number = f"RS-{datetime.now().strftime('%Y%m%d')}-{runsheet_id[:6].upper()}"
                        
                        runsheet_data = {
                            'entityID': runsheet_id,  # Partition key
                            'entityType': 'runsheet',  # Sort key  
                            'runsheetID': runsheet_id,
                            'runsheetNumber': runsheet_number,
                            'deliveryArea': group_data['pincode'],
                            'deliveryDate': group_data['delivery_date'],
                            'timeSlot': group_data['time_slot'],
                            'orderCount': len(orders),
                            'totalValue': runsheet_info['total_value'],
                            'orders': [
                                {
                                    'orderID': order.get('orderID'),
                                    'customerName': order.get('customerInfo', {}).get('name', 'Unknown'),
                                    'customerEmail': order.get('customerEmail'),
                                    'customerPhone': order.get('customerInfo', {}).get('phone', 'Unknown'),
                                    'deliveryAddress': order.get('deliveryAddress', {}),
                                    'items': order.get('items', []),
                                    'orderValue': order.get('orderSummary', {}).get('totalAmount', 0),
                                    'specialInstructions': order.get('specialInstructions', ''),
                                    'paymentMethod': order.get('paymentStatus', 'cod')
                                }
                                for order in orders
                            ],
                            'status': 'created',
                            'assignedRider': None,
                            'vehicleAssigned': None,
                            'estimatedDuration': len(orders) * 20,  # 20 mins per delivery
                            'estimatedDistance': len(orders) * 3,   # 3 km per delivery
                            'createdBy': self.current_user.get('userID', 'warehouse-manager'),
                            'createdAt': datetime.now(timezone.utc).isoformat(),
                            'updatedAt': datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Save runsheet to logistics table
                        self.logistics_table.put_item(Item=runsheet_data)
                        created_count += 1
                        created_runsheets.append(runsheet_data)
                        
                        print(f"   ✅ Created runsheet {runsheet_number} for {group_data['pincode']}")
                        print(f"      📦 {len(orders)} orders, 💰 ₹{runsheet_info['total_value']:,.2f}")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to create runsheet {i}: {str(e)}")
                
                self.print_success(f"Successfully created {created_count} runsheets!")
                
                if created_runsheets:
                    print(f"\n📋 CREATED RUNSHEETS SUMMARY:")
                    print("-" * 60)
                    total_orders = sum(rs['orderCount'] for rs in created_runsheets)
                    total_value = sum(rs['totalValue'] for rs in created_runsheets)
                    
                    print(f"📋 Total Runsheets: {len(created_runsheets)}")
                    print(f"📦 Total Orders: {total_orders}")
                    print(f"💰 Total Value: ₹{total_value:,.2f}")
                    print(f"🕒 Estimated Delivery Time: {sum(rs['estimatedDuration'] for rs in created_runsheets)} minutes")
                    print(f"🗺️ Estimated Distance: {sum(rs['estimatedDistance'] for rs in created_runsheets)} km")
                    
                    print(f"\n📋 Runsheet Details:")
                    for rs in created_runsheets:
                        print(f"   📋 {rs['runsheetNumber']} - {rs['deliveryArea']} ({rs['orderCount']} orders)")
                
                print(f"\n➡️ Next Step: Assign runsheets to riders (Option 4)")
            else:
                self.print_info("Runsheet creation cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to create runsheets: {str(e)}")
            input("Press Enter to continue...")

    def assign_runsheets(self):
        """Assign runsheets to riders"""
        try:
            self.print_header("ASSIGN RUNSHEETS TO RIDERS")
            
            # Get created runsheets (not yet assigned)
            response = self.logistics_table.scan(
                FilterExpression='#status = :status AND entityType = :entity_type',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'created',
                    ':entity_type': 'runsheet'
                }
            )
            available_runsheets = response.get('Items', [])
            
            if not available_runsheets:
                self.print_info("No runsheets available for assignment")
                print("💡 Tip: Create runsheets first (Option 3)")
                input("Press Enter to continue...")
                return
            
            print(f"📋 Found {len(available_runsheets)} runsheets ready for assignment:")
            print("-" * 80)
            
            # Available riders with their details
            available_riders = [
                {
                    'riderID': 'rider-001',
                    'name': 'Ravi Kumar',
                    'phone': '+91-9876543001',
                    'vehicle': 'Bike',
                    'license': 'DL-01-20230001',
                    'experience': '3 years',
                    'rating': 4.8,
                    'areas': ['500001', '500003', '500008']
                },
                {
                    'riderID': 'rider-002',
                    'name': 'Suresh Reddy',
                    'phone': '+91-9876543002',
                    'vehicle': 'Bike',
                    'license': 'DL-01-20230002',
                    'experience': '2 years',
                    'rating': 4.6,
                    'areas': ['500016', '500018', '500028']
                },
                {
                    'riderID': 'rider-003',
                    'name': 'Amit Singh',
                    'phone': '+91-9876543003',
                    'vehicle': 'Van',
                    'license': 'DL-01-20230003',
                    'experience': '5 years',
                    'rating': 4.9,
                    'areas': ['500072', '500081', '500084']
                },
                {
                    'riderID': 'rider-004',
                    'name': 'Priya Sharma',
                    'phone': '+91-9876543004',
                    'vehicle': 'Bike',
                    'license': 'DL-01-20230004',
                    'experience': '1 year',
                    'rating': 4.5,
                    'areas': ['500038', '500032', '500001']
                },
                {
                    'riderID': 'rider-005',
                    'name': 'Kiran Patel',
                    'phone': '+91-9876543005',
                    'vehicle': 'Van',
                    'license': 'DL-01-20230005',
                    'experience': '4 years',
                    'rating': 4.7,
                    'areas': ['500003', '500008', '500016']
                }
            ]
            
            # Display runsheets
            for i, runsheet in enumerate(available_runsheets, 1):
                runsheet_number = runsheet.get('runsheetNumber', 'Unknown')
                area = runsheet.get('deliveryArea', 'Unknown')
                order_count = runsheet.get('orderCount', 0)
                total_value = runsheet.get('totalValue', 0)
                time_slot = runsheet.get('timeSlot', 'Unknown')
                
                print(f"\n📋 {i}. Runsheet: {runsheet_number}")
                print(f"   📍 Area: {area}")
                print(f"   🕒 Time Slot: {time_slot}")
                print(f"   📦 Orders: {order_count}")
                print(f"   💰 Value: ₹{total_value:,.2f}")
                print(f"   🕒 Est. Duration: {runsheet.get('estimatedDuration', 0)} minutes")
            
            print(f"\n👥 AVAILABLE RIDERS:")
            print("-" * 60)
            for i, rider in enumerate(available_riders, 1):
                print(f"{i}. 🚴 {rider['name']} ({rider['vehicle']})")
                print(f"   📱 {rider['phone']}")
                print(f"   ⭐ Rating: {rider['rating']}/5.0")
                print(f"   📍 Areas: {', '.join(rider['areas'])}")
                print(f"   🎓 Experience: {rider['experience']}")
            
            assign_choice = input(f"\nAuto-assign runsheets to best-matched riders? (y/N): ").strip().lower()
            
            if assign_choice == 'y':
                assigned_count = 0
                assignment_details = []
                
                for runsheet in available_runsheets:
                    try:
                        runsheet_area = runsheet.get('deliveryArea', '')
                        
                        # Find best rider for this area
                        best_rider = None
                        best_score = 0
                        
                        for rider in available_riders:
                            score = 0
                            # Area match bonus (highest priority)
                            if runsheet_area in rider['areas']:
                                score += 10
                            # Rating bonus
                            score += rider['rating']
                            # Vehicle type bonus for large orders
                            if runsheet.get('orderCount', 0) > 5 and rider['vehicle'] == 'Van':
                                score += 3
                            
                            if score > best_score:
                                best_score = score
                                best_rider = rider
                        
                        if not best_rider:
                            best_rider = available_riders[assigned_count % len(available_riders)]
                        
                        # Convert rider data to DynamoDB-compatible format
                        rider_data = {
                            'riderID': best_rider['riderID'],
                            'name': best_rider['name'],
                            'phone': best_rider['phone'],
                            'vehicle': best_rider['vehicle'],
                            'license': best_rider['license'],
                            'experience': best_rider['experience'],
                            'rating': Decimal(str(best_rider['rating'])),  # Convert float to Decimal
                            'areas': best_rider['areas']
                        }
                        
                        # Assign runsheet to rider
                        self.logistics_table.update_item(
                            Key={
                                'entityID': runsheet['entityID'],
                                'entityType': runsheet['entityType']
                            },
                            UpdateExpression='SET #status = :status, assignedRider = :rider, assignedAt = :assigned, updatedAt = :updated',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':status': 'assigned',
                                ':rider': rider_data,
                                ':assigned': datetime.now(timezone.utc).isoformat(),
                                ':updated': datetime.now(timezone.utc).isoformat()
                            }
                        )
                        
                        # Update all orders in this runsheet to 'out_for_delivery'
                        updated_orders = 0
                        for order_data in runsheet.get('orders', []):
                            order_id = order_data.get('orderID')
                            customer_email = order_data.get('customerEmail')
                            
                            if order_id and customer_email:
                                try:
                                    self.orders_table.update_item(
                                        Key={
                                            'orderID': order_id,
                                            'customerEmail': customer_email
                                        },
                                        UpdateExpression='SET #status = :status, assignedRider = :rider, runsheetID = :runsheet_id, updatedAt = :updated',
                                        ExpressionAttributeNames={'#status': 'status'},
                                        ExpressionAttributeValues={
                                            ':status': 'out_for_delivery',
                                            ':rider': rider_data,
                                            ':runsheet_id': runsheet['runsheetID'],
                                            ':updated': datetime.now(timezone.utc).isoformat()
                                        }
                                    )
                                    updated_orders += 1
                                except Exception as e:
                                    print(f"      ⚠️ Failed to update order {order_id}: {str(e)}")
                        
                        assigned_count += 1
                        runsheet_number = runsheet.get('runsheetNumber', 'Unknown')
                        area_match = runsheet_area in best_rider['areas']
                        
                        assignment_details.append({
                            'runsheet': runsheet_number,
                            'rider': best_rider['name'],
                            'vehicle': best_rider['vehicle'],
                            'area_match': area_match,
                            'orders_updated': updated_orders
                        })
                        
                        print(f"   ✅ Assigned {runsheet_number} to {best_rider['name']} ({best_rider['vehicle']})")
                        print(f"      📍 Area match: {'✅' if area_match else '⚠️'} | Orders updated: {updated_orders}")
                        
                    except Exception as e:
                        print(f"   ❌ Failed to assign runsheet: {str(e)}")
                
                self.print_success(f"Successfully assigned {assigned_count} runsheets!")
                
                if assignment_details:
                    print(f"\n📊 ASSIGNMENT SUMMARY:")
                    print("-" * 60)
                    total_orders_dispatched = sum(detail['orders_updated'] for detail in assignment_details)
                    perfect_matches = sum(1 for detail in assignment_details if detail['area_match'])
                    
                    print(f"   📋 Runsheets Assigned: {assigned_count}")
                    print(f"   📦 Orders Dispatched: {total_orders_dispatched}")
                    print(f"   👥 Riders Utilized: {len(set(detail['rider'] for detail in assignment_details))}")
                    print(f"   🎯 Perfect Area Matches: {perfect_matches}/{assigned_count}")
                    
                    print(f"\n📋 Assignment Details:")
                    for detail in assignment_details:
                        match_icon = '✅' if detail['area_match'] else '⚠️'
                        print(f"   {match_icon} {detail['runsheet']} → {detail['rider']} ({detail['vehicle']})")
                
                print(f"\n🚚 Orders are now out for delivery with assigned riders!")
                print(f"📱 Riders can track their runsheets and update delivery status")
                
            else:
                self.print_info("Runsheet assignment cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to assign runsheets: {str(e)}")
            input("Press Enter to continue...")

    def delivery_tracking(self):
        """Track ongoing deliveries"""
        try:
            self.print_header("DELIVERY TRACKING")
            
            print("📱 REAL-TIME DELIVERY TRACKING")
            print("=" * 60)
            
            # Get orders in delivery status
            orders_response = self.orders_table.scan(
                FilterExpression='#status IN (:shipped, :out_for_delivery)',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':shipped': 'shipped',
                    ':out_for_delivery': 'out_for_delivery'
                }
            )
            
            active_deliveries = orders_response.get('Items', [])
            
            if not active_deliveries:
                print("✅ No active deliveries at the moment")
                return
            
            print(f"🚚 ACTIVE DELIVERIES ({len(active_deliveries)}):")
            print("-" * 50)
            
            for delivery in sorted(active_deliveries, key=lambda x: x.get('orderDate', '')):
                order_id = delivery.get('orderID', 'N/A')
                order_number = delivery.get('orderNumber', 'N/A')
                status = delivery.get('status', 'unknown')
                customer_info = delivery.get('customerInfo', {})
                customer_name = customer_info.get('name', 'Unknown Customer')
                delivery_address = delivery.get('deliveryAddress', {})
                city = delivery_address.get('city', 'Unknown')
                pincode = delivery.get('deliveryPincode', 'N/A')
                time_slot = delivery.get('deliveryTimeSlot', 'N/A')
                
                status_emoji = "📦" if status == 'shipped' else "🚚" if status == 'out_for_delivery' else "❓"
                
                print(f"\n{status_emoji} ORDER #{order_number}")
                print(f"   👤 Customer: {customer_name}")
                print(f"   📍 Location: {city} - {pincode}")
                print(f"   🕒 Time Slot: {time_slot}")
                print(f"   📊 Status: {status.replace('_', ' ').title()}")
                
                # Estimated delivery time (simplified)
                if status == 'shipped':
                    print(f"   ⏱️  ETA: Preparing for dispatch")
                elif status == 'out_for_delivery':
                    print(f"   ⏱️  ETA: Within delivery window")
            
            print(f"\n📊 DELIVERY SUMMARY:")
            shipped_count = len([d for d in active_deliveries if d.get('status') == 'shipped'])
            out_for_delivery_count = len([d for d in active_deliveries if d.get('status') == 'out_for_delivery'])
            
            print(f"   📦 Shipped: {shipped_count}")
            print(f"   🚚 Out for Delivery: {out_for_delivery_count}")
            
            # Performance metrics
            total_value = sum(float(d.get('pricing', {}).get('finalAmount', 0)) for d in active_deliveries)
            print(f"   💰 Total Value in Transit: ₹{total_value:,.2f}")
            
        except Exception as e:
            self.print_error(f"Failed to load delivery tracking: {str(e)}")

    def route_optimization(self):
        """Route optimization algorithms and suggestions"""
        try:
            self.print_header("ROUTE OPTIMIZATION")
            
            print("🎯 INTELLIGENT ROUTE OPTIMIZATION")
            print("=" * 60)
            
            # Get delivery data for analysis
            today = datetime.now(timezone.utc).date().isoformat()
            
            orders_response = self.orders_table.query(
                IndexName='DeliveryDateIndex',
                KeyConditionExpression='deliveryDate = :today',
                ExpressionAttributeValues={':today': today}
            )
            
            orders = orders_response.get('Items', [])
            
            if not orders:
                print("📋 No orders to optimize for today")
                return
            
            # Analyze current routes
            print(f"📊 ROUTE ANALYSIS ({len(orders)} orders):")
            print("-" * 50)
            
            # Group by pincode and time slot
            route_analysis = {}
            for order in orders:
                pincode = order.get('deliveryPincode', 'unknown')
                time_slot = order.get('deliveryTimeSlot', 'unknown')
                key = f"{pincode}-{time_slot}"
                
                if key not in route_analysis:
                    route_analysis[key] = {
                        'pincode': pincode,
                        'time_slot': time_slot,
                        'orders': [],
                        'total_value': 0,
                        'addresses': set()
                    }
                
                route_analysis[key]['orders'].append(order)
                route_analysis[key]['total_value'] += float(order.get('pricing', {}).get('finalAmount', 0))
                
                address = order.get('deliveryAddress', {})
                street = address.get('street', 'Unknown')
                route_analysis[key]['addresses'].add(street)
            
            # Display optimization analysis
            for route_key, route_data in sorted(route_analysis.items()):
                pincode = route_data['pincode']
                time_slot = route_data['time_slot']
                order_count = len(route_data['orders'])
                total_value = route_data['total_value']
                unique_addresses = len(route_data['addresses'])
                
                print(f"\n🚛 ROUTE: {pincode} ({time_slot})")
                print(f"   📦 Orders: {order_count}")
                print(f"   💰 Value: ₹{total_value:,.2f}")
                print(f"   📍 Unique Addresses: {unique_addresses}")
                
                # Optimization score (simplified)
                efficiency_score = order_count / max(unique_addresses, 1) * 100
                if efficiency_score > 150:
                    print(f"   ✅ Efficiency: Excellent ({efficiency_score:.0f}%)")
                elif efficiency_score > 100:
                    print(f"   🟡 Efficiency: Good ({efficiency_score:.0f}%)")
                else:
                    print(f"   🔴 Efficiency: Needs optimization ({efficiency_score:.0f}%)")
            
            # Optimization recommendations
            print(f"\n🎯 OPTIMIZATION RECOMMENDATIONS:")
            print("-" * 50)
            
            # Check for route consolidation opportunities
            pincodes = set(route_data['pincode'] for route_data in route_analysis.values())
            time_slots = set(route_data['time_slot'] for route_data in route_analysis.values())
            
            print(f"📊 Current Configuration:")
            print(f"   📍 Pincodes: {len(pincodes)}")
            print(f"   🕒 Time Slots: {len(time_slots)}")
            print(f"   🚛 Total Route Combinations: {len(route_analysis)}")
            
            print(f"\n💡 Suggestions:")
            if len(route_analysis) > 8:
                print("   🔄 Consider consolidating nearby pincodes")
            if any(len(route_data['orders']) < 3 for route_data in route_analysis.values()):
                print("   📦 Some routes have low order density - consider merging")
            if any(len(route_data['orders']) > 25 for route_data in route_analysis.values()):
                print("   📦 Some routes are overloaded - consider splitting")
            
            print("   ⛽ Optimize fuel consumption by grouping nearby deliveries")
            print("   🕒 Balance workload across time slots")
            print("   📱 Use GPS tracking for real-time route adjustments")
            
        except Exception as e:
            self.print_error(f"Failed to load route optimization: {str(e)}")

    def driver_management(self):
        """Manage delivery drivers and assignments"""
        try:
            self.print_header("DRIVER MANAGEMENT")
            
            print("👥 DELIVERY DRIVER MANAGEMENT")
            print("=" * 60)
            
            # Get staff with delivery roles
            staff_response = self.staff_table.scan(
                FilterExpression='contains(#roles, :role)',
                ExpressionAttributeNames={'#roles': 'roles'},
                ExpressionAttributeValues={':role': 'delivery_personnel'}
            )
            
            drivers = staff_response.get('Items', [])
            
            if not drivers:
                print("👥 No delivery drivers found in staff database")
                return
            
            print(f"👥 AVAILABLE DRIVERS ({len(drivers)}):")
            print("-" * 50)
            
            for driver in sorted(drivers, key=lambda x: x.get('name', '')):
                name = driver.get('name', 'Unknown Driver')
                employee_id = driver.get('employeeID', 'N/A')
                status = driver.get('status', 'unknown')
                shift = driver.get('currentShift', 'N/A')
                
                status_emoji = "✅" if status == 'active' else "🔴" if status == 'inactive' else "🟡"
                
                print(f"\n{status_emoji} {name}")
                print(f"   🆔 ID: {employee_id}")
                print(f"   📊 Status: {status.title()}")
                print(f"   🕒 Shift: {shift}")
                
                # Driver performance (simplified)
                deliveries_today = random.randint(0, 15)  # In real system, query actual data
                print(f"   📦 Deliveries Today: {deliveries_today}")
                
                if driver.get('vehicleAssigned'):
                    print(f"   🚛 Vehicle: {driver['vehicleAssigned']}")
            
            print(f"\n📊 DRIVER STATISTICS:")
            active_drivers = len([d for d in drivers if d.get('status') == 'active'])
            print(f"   ✅ Active Drivers: {active_drivers}")
            print(f"   👥 Total Drivers: {len(drivers)}")
            
            if active_drivers > 0:
                avg_deliveries = sum(random.randint(0, 15) for _ in range(active_drivers)) / active_drivers
                print(f"   📊 Average Deliveries/Driver: {avg_deliveries:.1f}")
            
            print(f"\n🎯 DRIVER MANAGEMENT OPTIONS:")
            print("   1. 📋 View driver performance")
            print("   2. 🚛 Assign vehicles to drivers")
            print("   3. 📍 Assign routes to drivers")
            print("   4. 🕒 Manage driver schedules")
            print("   5. 📊 Driver analytics")
            
        except Exception as e:
            self.print_error(f"Failed to load driver management: {str(e)}")

    def fuel_management(self):
        """Fuel consumption tracking and management"""
        try:
            self.print_header("FUEL MANAGEMENT")
            
            print("⛽ FUEL CONSUMPTION TRACKING")
            print("=" * 60)
            
            # Get logistics/vehicle data
            logistics_response = self.logistics_table.scan()
            logistics_data = logistics_response.get('Items', [])
            
            vehicles = [item for item in logistics_data if item.get('entityType') == 'vehicle']
            
            if not vehicles:
                print("🚛 No vehicle data available")
                return
            
            print(f"🚛 VEHICLE FUEL STATUS ({len(vehicles)} vehicles):")
            print("-" * 50)
            
            total_fuel_cost = 0
            total_distance = 0
            
            for vehicle in vehicles:
                vehicle_id = vehicle.get('vehicleID', 'N/A')
                vehicle_type = vehicle.get('vehicleType', 'Unknown')
                fuel_level = vehicle.get('fuelLevel', 0)
                mileage = vehicle.get('mileage', 15)  # km per liter
                
                # Simulated data for demonstration
                daily_distance = random.randint(50, 200)
                fuel_consumed = daily_distance / mileage
                fuel_cost = fuel_consumed * 100  # ₹100 per liter
                
                total_distance += daily_distance
                total_fuel_cost += fuel_cost
                
                status_emoji = "🟢" if fuel_level > 50 else "🟡" if fuel_level > 20 else "🔴"
                
                print(f"\n🚛 {vehicle_id} ({vehicle_type})")
                print(f"   {status_emoji} Fuel Level: {fuel_level}%")
                print(f"   📏 Distance Today: {daily_distance} km")
                print(f"   ⛽ Fuel Consumed: {fuel_consumed:.1f} L")
                print(f"   💰 Fuel Cost: ₹{fuel_cost:.2f}")
                print(f"   📊 Mileage: {mileage} km/L")
                
                if fuel_level < 25:
                    print(f"   ⚠️  LOW FUEL - Refuel required")
            
            print(f"\n📊 FLEET FUEL SUMMARY:")
            print(f"   🚛 Total Vehicles: {len(vehicles)}")
            print(f"   📏 Total Distance: {total_distance} km")
            print(f"   💰 Total Fuel Cost: ₹{total_fuel_cost:.2f}")
            
            if len(vehicles) > 0:
                avg_mileage = sum(v.get('mileage', 15) for v in vehicles) / len(vehicles)
                print(f"   📊 Average Mileage: {avg_mileage:.1f} km/L")
            
            # Fuel efficiency recommendations
            print(f"\n💡 FUEL EFFICIENCY RECOMMENDATIONS:")
            print("   🎯 Optimize routes to reduce total distance")
            print("   🚛 Regular vehicle maintenance for better mileage")
            print("   📊 Monitor driver behavior for fuel efficiency")
            print("   ⛽ Bulk fuel purchases for cost savings")
            print("   📱 Use fuel tracking apps for real-time monitoring")
            
            # Fuel alerts
            low_fuel_vehicles = [v for v in vehicles if v.get('fuelLevel', 100) < 25]
            if low_fuel_vehicles:
                print(f"\n🚨 FUEL ALERTS:")
                for vehicle in low_fuel_vehicles:
                    print(f"   🔴 {vehicle.get('vehicleID', 'N/A')} needs refueling")
            
        except Exception as e:
            self.print_error(f"Failed to load fuel management: {str(e)}")

    def vehicle_maintenance(self):
        """Vehicle maintenance tracking and scheduling"""
        try:
            self.print_header("VEHICLE MAINTENANCE")
            
            print("🔧 VEHICLE MAINTENANCE MANAGEMENT")
            print("=" * 60)
            
            # Get vehicle data
            logistics_response = self.logistics_table.scan()
            logistics_data = logistics_response.get('Items', [])
            
            vehicles = [item for item in logistics_data if item.get('entityType') == 'vehicle']
            
            if not vehicles:
                print("🚛 No vehicle data available")
                return
            
            print(f"🚛 VEHICLE MAINTENANCE STATUS ({len(vehicles)} vehicles):")
            print("-" * 50)
            
            maintenance_due = []
            
            for vehicle in vehicles:
                vehicle_id = vehicle.get('vehicleID', 'N/A')
                vehicle_type = vehicle.get('vehicleType', 'Unknown')
                status = vehicle.get('status', 'unknown')
                
                # Simulated maintenance data
                last_service = datetime.now() - timedelta(days=random.randint(30, 180))
                next_service = last_service + timedelta(days=90)  # Service every 90 days
                days_until_service = (next_service.date() - datetime.now().date()).days
                
                odometer = random.randint(50000, 150000)
                next_service_km = odometer + random.randint(5000, 15000)
                
                # Maintenance status
                if days_until_service < 0:
                    maintenance_status = "🔴 OVERDUE"
                    maintenance_due.append(vehicle)
                elif days_until_service < 7:
                    maintenance_status = "🟡 DUE SOON"
                    maintenance_due.append(vehicle)
                else:
                    maintenance_status = "🟢 UP TO DATE"
                
                print(f"\n🚛 {vehicle_id} ({vehicle_type})")
                print(f"   📊 Status: {status.title()}")
                print(f"   {maintenance_status}")
                print(f"   📅 Last Service: {last_service.strftime('%Y-%m-%d')}")
                print(f"   📅 Next Service: {next_service.strftime('%Y-%m-%d')} ({days_until_service} days)")
                print(f"   📏 Odometer: {odometer:,} km")
                print(f"   🔧 Next Service: {next_service_km:,} km")
                
                # Maintenance items
                maintenance_items = [
                    "Oil Change", "Brake Check", "Tire Rotation", 
                    "Battery Check", "Air Filter", "Coolant Level"
                ]
                pending_items = random.sample(maintenance_items, random.randint(1, 3))
                
                if pending_items:
                    print(f"   📋 Pending: {', '.join(pending_items)}")
            
            print(f"\n📊 MAINTENANCE SUMMARY:")
            print(f"   🚛 Total Vehicles: {len(vehicles)}")
            print(f"   🔧 Maintenance Due: {len(maintenance_due)}")
            
            overdue = len([v for v in maintenance_due if (datetime.now().date() - (datetime.now() - timedelta(days=random.randint(30, 180))).date()).days > 90])
            due_soon = len(maintenance_due) - overdue
            
            print(f"   🔴 Overdue: {overdue}")
            print(f"   🟡 Due Soon: {due_soon}")
            
            # Maintenance schedule
            if maintenance_due:
                print(f"\n📅 MAINTENANCE SCHEDULE:")
                print("-" * 40)
                for vehicle in maintenance_due[:5]:  # Show top 5
                    vehicle_id = vehicle.get('vehicleID', 'N/A')
                    print(f"   🔧 {vehicle_id} - Schedule maintenance")
            
            print(f"\n💡 MAINTENANCE RECOMMENDATIONS:")
            print("   📅 Schedule regular preventive maintenance")
            print("   📊 Track maintenance costs and patterns")
            print("   🔧 Use certified service centers")
            print("   📱 Set up maintenance reminders")
            print("   📋 Keep detailed maintenance records")
            
        except Exception as e:
            self.print_error(f"Failed to load vehicle maintenance: {str(e)}")

    def logistics_analytics(self):
        """Comprehensive logistics analytics and insights"""
        try:
            self.print_header("LOGISTICS ANALYTICS")
            
            print("📊 LOGISTICS PERFORMANCE ANALYTICS")
            print("=" * 70)
            
            # Get orders data for logistics analysis
            orders_response = self.orders_table.scan()
            orders = orders_response.get('Items', [])
            
            if not orders:
                print("📋 No order data available for analytics")
                return
            
            # Delivery performance analysis
            delivered_orders = [o for o in orders if o.get('status') == 'delivered']
            total_orders = len(orders)
            delivery_rate = (len(delivered_orders) / total_orders * 100) if total_orders > 0 else 0
            
            print(f"📦 DELIVERY PERFORMANCE:")
            print(f"   📋 Total Orders: {total_orders:,}")
            print(f"   ✅ Delivered: {len(delivered_orders):,}")
            print(f"   📊 Delivery Rate: {delivery_rate:.1f}%")
            
            # On-time delivery analysis (simplified)
            on_time_deliveries = random.randint(int(len(delivered_orders) * 0.7), len(delivered_orders))
            on_time_rate = (on_time_deliveries / len(delivered_orders) * 100) if delivered_orders else 0
            
            print(f"   ⏰ On-Time Deliveries: {on_time_deliveries:,}")
            print(f"   📊 On-Time Rate: {on_time_rate:.1f}%")
            
            # Geographic analysis
            print(f"\n📍 GEOGRAPHIC DISTRIBUTION:")
            pincode_stats = {}
            for order in orders:
                pincode = order.get('deliveryPincode', 'unknown')
                if pincode not in pincode_stats:
                    pincode_stats[pincode] = {'orders': 0, 'delivered': 0, 'value': 0}
                
                pincode_stats[pincode]['orders'] += 1
                if order.get('status') == 'delivered':
                    pincode_stats[pincode]['delivered'] += 1
                
                pincode_stats[pincode]['value'] += float(order.get('pricing', {}).get('finalAmount', 0))
            
            # Top pincodes by volume
            top_pincodes = sorted(pincode_stats.items(), key=lambda x: x[1]['orders'], reverse=True)[:5]
            
            for pincode, stats in top_pincodes:
                delivery_rate = (stats['delivered'] / stats['orders'] * 100) if stats['orders'] > 0 else 0
                print(f"   📍 {pincode}: {stats['orders']} orders ({delivery_rate:.1f}% delivered)")
            
            # Time slot analysis
            print(f"\n🕒 TIME SLOT PERFORMANCE:")
            time_slot_stats = {}
            for order in orders:
                time_slot = order.get('deliveryTimeSlot', 'unknown')
                if time_slot not in time_slot_stats:
                    time_slot_stats[time_slot] = {'orders': 0, 'delivered': 0}
                
                time_slot_stats[time_slot]['orders'] += 1
                if order.get('status') == 'delivered':
                    time_slot_stats[time_slot]['delivered'] += 1
            
            for time_slot, stats in sorted(time_slot_stats.items()):
                delivery_rate = (stats['delivered'] / stats['orders'] * 100) if stats['orders'] > 0 else 0
                print(f"   🕒 {time_slot}: {stats['orders']} orders ({delivery_rate:.1f}% delivered)")
            
            # Cost analysis
            print(f"\n💰 LOGISTICS COST ANALYSIS:")
            total_delivery_value = sum(float(o.get('pricing', {}).get('finalAmount', 0)) for o in delivered_orders)
            
            # Estimated logistics costs (simplified)
            fuel_cost = len(delivered_orders) * 50  # ₹50 per delivery
            driver_cost = len(delivered_orders) * 30  # ₹30 per delivery
            vehicle_cost = len(delivered_orders) * 20  # ₹20 per delivery
            total_logistics_cost = fuel_cost + driver_cost + vehicle_cost
            
            print(f"   💰 Total Delivery Value: ₹{total_delivery_value:,.2f}")
            print(f"   ⛽ Fuel Costs: ₹{fuel_cost:,.2f}")
            print(f"   👥 Driver Costs: ₹{driver_cost:,.2f}")
            print(f"   🚛 Vehicle Costs: ₹{vehicle_cost:,.2f}")
            print(f"   📊 Total Logistics Cost: ₹{total_logistics_cost:,.2f}")
            
            if total_delivery_value > 0:
                cost_percentage = (total_logistics_cost / total_delivery_value * 100)
                print(f"   📊 Logistics Cost %: {cost_percentage:.1f}%")
            
            # Performance insights
            print(f"\n🎯 PERFORMANCE INSIGHTS:")
            if delivery_rate > 95:
                print("   ✅ Excellent delivery performance")
            elif delivery_rate > 85:
                print("   🟡 Good delivery performance")
            else:
                print("   🔴 Delivery performance needs improvement")
            
            if on_time_rate > 90:
                print("   ✅ Excellent on-time performance")
            elif on_time_rate > 80:
                print("   🟡 Good on-time performance")
            else:
                print("   🔴 On-time performance needs improvement")
            
            print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
            print("   📍 Focus on underperforming pincodes")
            print("   🕒 Optimize time slot allocation")
            print("   🚛 Improve route efficiency")
            print("   📊 Monitor cost per delivery")
            print("   📱 Implement real-time tracking")
            
        except Exception as e:
            self.print_error(f"Failed to load logistics analytics: {str(e)}")

    def delivery_slots_management(self):
        """Comprehensive delivery slots management"""
        while True:
            self.print_header("DELIVERY SLOTS MANAGEMENT")
            print("🕒 DELIVERY SLOTS MANAGEMENT OPTIONS:")
            print("-" * 70)
            print("1. 📋 View All Delivery Slots")
            print("2. ➕ Create New Delivery Slot")
            print("3. ✏️  Edit Delivery Slot")
            print("4. 🗑️  Delete Delivery Slot")
            print("5. 📍 Manage Pincode Serviceability")
            print("6. 📊 Slot Utilization Analytics")
            print("7. 📅 Bulk Slot Creation")
            print("8. 🔍 Search Slots by Pincode")
            print("9. 📈 Slot Performance Report")
            print("0. ⬅️  Back to Logistics Menu")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.view_all_delivery_slots()
            elif choice == '2':
                self.create_delivery_slot()
            elif choice == '3':
                self.edit_delivery_slot()
            elif choice == '4':
                self.delete_delivery_slot()
            elif choice == '5':
                self.manage_pincode_serviceability()
            elif choice == '6':
                self.slot_utilization_analytics()
            elif choice == '7':
                self.bulk_slot_creation()
            elif choice == '8':
                self.search_slots_by_pincode()
            elif choice == '9':
                self.slot_performance_report()
            else:
                self.print_error("Invalid choice. Please try again.")
            
            if choice != '0':
                input("\nPress Enter to continue...")

    def view_all_delivery_slots(self):
        """View all delivery slots"""
        try:
            self.print_header("ALL DELIVERY SLOTS")
            
            # Get all delivery slots
            response = self.delivery_table.scan()
            slots = response.get('Items', [])
            
            if not slots:
                self.print_info("No delivery slots found")
                return
            
            print(f"📋 TOTAL DELIVERY SLOTS: {len(slots)}")
            print("=" * 80)
            
            # Group by pincode
            slots_by_pincode = {}
            for slot in slots:
                pincode = slot.get('pincode', 'Unknown')
                if pincode not in slots_by_pincode:
                    slots_by_pincode[pincode] = []
                slots_by_pincode[pincode].append(slot)
            
            for pincode, pincode_slots in sorted(slots_by_pincode.items()):
                print(f"\n📍 PINCODE: {pincode}")
                print("-" * 60)
                
                for slot in sorted(pincode_slots, key=lambda x: x.get('slotInfo', {}).get('timeSlot', '')):
                    slot_id = slot.get('slotID', 'N/A')
                    slot_info = slot.get('slotInfo', {})
                    time_slot = slot_info.get('timeSlot', 'N/A')
                    slot_type = slot_info.get('slotType', 'N/A')
                    max_orders = slot_info.get('maxOrders', 0)
                    current_orders = slot_info.get('currentOrders', 0)
                    delivery_charge = slot_info.get('deliveryCharge', 0)
                    is_active = slot_info.get('isActive', 'false') == 'true'
                    
                    status_emoji = "✅" if is_active else "❌"
                    utilization = (current_orders / max_orders * 100) if max_orders > 0 else 0
                    
                    print(f"   🕒 {time_slot} ({slot_type.title()}) {status_emoji}")
                    print(f"      🆔 Slot ID: {slot_id}")
                    print(f"      📦 Capacity: {current_orders}/{max_orders} ({utilization:.1f}%)")
                    print(f"      💰 Delivery Charge: ₹{delivery_charge}")
                    print()
                    
        except Exception as e:
            self.print_error(f"Failed to load delivery slots: {str(e)}")

    def create_delivery_slot(self):
        """Create new delivery slot"""
        try:
            self.print_header("CREATE NEW DELIVERY SLOT")
            
            # Get pincode
            pincode = input("📍 Enter Pincode: ").strip()
            if not pincode or len(pincode) != 6 or not pincode.isdigit():
                self.print_error("Invalid pincode. Must be 6 digits.")
                return
            
            # Get time slot
            print("\n🕒 TIME SLOT OPTIONS:")
            print("1. 09:00-12:00 (Morning)")
            print("2. 14:00-17:00 (Afternoon)")
            print("3. 18:00-21:00 (Evening)")
            print("4. Custom Time Slot")
            
            time_choice = input("Select time slot (1-4): ").strip()
            
            if time_choice == '1':
                time_slot = '09:00-12:00'
                slot_type = 'morning'
            elif time_choice == '2':
                time_slot = '14:00-17:00'
                slot_type = 'afternoon'
            elif time_choice == '3':
                time_slot = '18:00-21:00'
                slot_type = 'evening'
            elif time_choice == '4':
                time_slot = input("Enter custom time slot (HH:MM-HH:MM): ").strip()
                slot_type = input("Enter slot type (morning/afternoon/evening/custom): ").strip().lower()
            else:
                self.print_error("Invalid choice")
                return
            
            # Get capacity
            try:
                max_orders = int(input("📦 Maximum orders capacity: ").strip())
                if max_orders <= 0:
                    self.print_error("Capacity must be greater than 0")
                    return
            except ValueError:
                self.print_error("Invalid capacity. Must be a number.")
                return
            
            # Get delivery charge
            try:
                delivery_charge = float(input("💰 Delivery charge (₹): ").strip())
                if delivery_charge < 0:
                    self.print_error("Delivery charge cannot be negative")
                    return
            except ValueError:
                self.print_error("Invalid delivery charge. Must be a number.")
                return
            
            # Check if slot already exists
            slot_id = f"slot-{pincode}-{slot_type}"
            
            try:
                existing_slot = self.delivery_table.get_item(
                    Key={'pincode': pincode, 'slotID': slot_id}
                )
                if 'Item' in existing_slot:
                    self.print_error("A slot with this pincode and type already exists")
                    return
            except:
                pass  # Slot doesn't exist, which is good
            
            # Create the slot
            from decimal import Decimal
            
            slot_data = {
                'pincode': pincode,
                'slotID': slot_id,
                'timeSlot': time_slot,
                'slotType': slot_type,
                'maxOrders': max_orders,
                'currentOrders': 0,
                'deliveryCharge': Decimal(str(delivery_charge)),
                'isActive': True,
                'serviceableAreas': [pincode],
                'slotInfo': {
                    'timeSlot': time_slot,
                    'slotType': slot_type,
                    'maxOrders': max_orders,
                    'currentOrders': 0,
                    'deliveryCharge': Decimal(str(delivery_charge)),
                    'isActive': True
                },
                'availableSlots': [
                    {
                        'slot': time_slot,
                        'type': slot_type,
                        'capacity': max_orders
                    }
                ],
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat(),
                'createdBy': self.current_user.get('userID', 'system')
            }
            
            # Insert the slot
            self.delivery_table.put_item(Item=slot_data)
            
            self.print_success("Delivery slot created successfully!")
            print(f"🆔 Slot ID: {slot_id}")
            print(f"📍 Pincode: {pincode}")
            print(f"🕒 Time Slot: {time_slot}")
            print(f"📦 Capacity: {max_orders} orders")
            print(f"💰 Delivery Charge: ₹{delivery_charge}")
            
        except Exception as e:
            self.print_error(f"Failed to create delivery slot: {str(e)}")

    def edit_delivery_slot(self):
        """Edit existing delivery slot"""
        try:
            self.print_header("EDIT DELIVERY SLOT")
            
            # Get pincode and slot ID
            pincode = input("📍 Enter Pincode: ").strip()
            if not pincode:
                self.print_error("Pincode is required")
                return
            
            # Show available slots for this pincode
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            if not slots:
                self.print_error(f"No delivery slots found for pincode {pincode}")
                return
            
            print(f"\n📋 AVAILABLE SLOTS FOR PINCODE {pincode}:")
            for i, slot in enumerate(slots, 1):
                time_slot = slot.get('timeSlot', 'N/A')
                slot_type = slot.get('slotType', 'N/A')
                is_active = slot.get('isActive', False)
                status = "✅ Active" if is_active else "❌ Inactive"
                print(f"{i}. {time_slot} ({slot_type.title()}) - {status}")
            
            try:
                choice = int(input(f"\nSelect slot to edit (1-{len(slots)}): ").strip())
                if not (1 <= choice <= len(slots)):
                    self.print_error("Invalid choice")
                    return
                
                selected_slot = slots[choice - 1]
                slot_id = selected_slot['slotID']
                
            except ValueError:
                self.print_error("Invalid choice. Must be a number.")
                return
            
            # Show current values and edit options
            print(f"\n✏️  EDITING SLOT: {selected_slot.get('timeSlot', 'N/A')}")
            print("=" * 50)
            print("1. 📦 Update Capacity")
            print("2. 💰 Update Delivery Charge")
            print("3. ✅ Toggle Active Status")
            print("4. 🕒 Update Time Slot")
            print("0. ❌ Cancel")
            
            edit_choice = input("\nSelect what to edit: ").strip()
            
            update_expression = "SET updatedAt = :updated"
            expression_values = {':updated': datetime.now(timezone.utc).isoformat()}
            
            if edit_choice == '1':
                try:
                    new_capacity = int(input(f"📦 New capacity (current: {selected_slot.get('maxOrders', 0)}): ").strip())
                    if new_capacity <= 0:
                        self.print_error("Capacity must be greater than 0")
                        return
                    
                    update_expression += ", maxOrders = :capacity, slotInfo.maxOrders = :capacity"
                    expression_values[':capacity'] = new_capacity
                    
                except ValueError:
                    self.print_error("Invalid capacity. Must be a number.")
                    return
                    
            elif edit_choice == '2':
                try:
                    new_charge = float(input(f"💰 New delivery charge (current: ₹{selected_slot.get('deliveryCharge', 0)}): ").strip())
                    if new_charge < 0:
                        self.print_error("Delivery charge cannot be negative")
                        return
                    
                    from decimal import Decimal
                    update_expression += ", deliveryCharge = :charge, slotInfo.deliveryCharge = :charge"
                    expression_values[':charge'] = Decimal(str(new_charge))
                    
                except ValueError:
                    self.print_error("Invalid delivery charge. Must be a number.")
                    return
                    
            elif edit_choice == '3':
                current_status = selected_slot.get('isActive', False)
                new_status = not current_status
                status_text = "Active" if new_status else "Inactive"
                
                confirm = input(f"✅ Change status to {status_text}? (y/n): ").strip().lower()
                if confirm == 'y':
                    update_expression += ", isActive = :status, slotInfo.isActive = :status"
                    expression_values[':status'] = new_status
                else:
                    self.print_info("Status change cancelled")
                    return
                    
            elif edit_choice == '4':
                new_time_slot = input(f"🕒 New time slot (current: {selected_slot.get('timeSlot', 'N/A')}): ").strip()
                if not new_time_slot:
                    self.print_error("Time slot cannot be empty")
                    return
                
                update_expression += ", timeSlot = :time_slot, slotInfo.timeSlot = :time_slot"
                expression_values[':time_slot'] = new_time_slot
                
            elif edit_choice == '0':
                self.print_info("Edit cancelled")
                return
            else:
                self.print_error("Invalid choice")
                return
            
            # Update the slot
            self.delivery_table.update_item(
                Key={'pincode': pincode, 'slotID': slot_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            self.print_success("Delivery slot updated successfully!")
            
        except Exception as e:
            self.print_error(f"Failed to edit delivery slot: {str(e)}")

    def delete_delivery_slot(self):
        """Delete delivery slot"""
        try:
            self.print_header("DELETE DELIVERY SLOT")
            
            # Get pincode
            pincode = input("📍 Enter Pincode: ").strip()
            if not pincode:
                self.print_error("Pincode is required")
                return
            
            # Show available slots
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            if not slots:
                self.print_error(f"No delivery slots found for pincode {pincode}")
                return
            
            print(f"\n📋 AVAILABLE SLOTS FOR PINCODE {pincode}:")
            for i, slot in enumerate(slots, 1):
                time_slot = slot.get('timeSlot', 'N/A')
                slot_type = slot.get('slotType', 'N/A')
                current_orders = slot.get('currentOrders', 0)
                print(f"{i}. {time_slot} ({slot_type.title()}) - {current_orders} active orders")
            
            try:
                choice = int(input(f"\nSelect slot to delete (1-{len(slots)}): ").strip())
                if not (1 <= choice <= len(slots)):
                    self.print_error("Invalid choice")
                    return
                
                selected_slot = slots[choice - 1]
                slot_id = selected_slot['slotID']
                current_orders = selected_slot.get('currentOrders', 0)
                
            except ValueError:
                self.print_error("Invalid choice. Must be a number.")
                return
            
            # Warn if there are active orders
            if current_orders > 0:
                print(f"\n⚠️  WARNING: This slot has {current_orders} active orders!")
                print("Deleting this slot may affect existing deliveries.")
                
            # Confirm deletion
            time_slot = selected_slot.get('timeSlot', 'N/A')
            confirm = input(f"\n❌ Are you sure you want to delete slot '{time_slot}' for pincode {pincode}? (y/n): ").strip().lower()
            
            if confirm != 'y':
                self.print_info("Deletion cancelled")
                return
            
            # Delete the slot
            self.delivery_table.delete_item(
                Key={'pincode': pincode, 'slotID': slot_id}
            )
            
            self.print_success(f"Delivery slot '{time_slot}' deleted successfully!")
            
        except Exception as e:
            self.print_error(f"Failed to delete delivery slot: {str(e)}")

    def manage_pincode_serviceability(self):
        """Manage pincode serviceability"""
        try:
            self.print_header("PINCODE SERVICEABILITY MANAGEMENT")
            
            print("📍 SERVICEABILITY OPTIONS:")
            print("-" * 50)
            print("1. 📋 View All Serviceable Pincodes")
            print("2. ➕ Add New Serviceable Pincode")
            print("3. ❌ Remove Pincode Serviceability")
            print("4. 🔍 Check Pincode Status")
            print("0. ⬅️  Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                self._view_serviceable_pincodes()
            elif choice == '2':
                self._add_serviceable_pincode()
            elif choice == '3':
                self._remove_pincode_serviceability()
            elif choice == '4':
                self._check_pincode_status()
            elif choice == '0':
                return
            else:
                self.print_error("Invalid choice")
                
        except Exception as e:
            self.print_error(f"Failed to manage pincode serviceability: {str(e)}")

    def _view_serviceable_pincodes(self):
        """View all serviceable pincodes"""
        try:
            response = self.delivery_table.scan()
            slots = response.get('Items', [])
            
            if not slots:
                self.print_info("No serviceable pincodes found")
                return
            
            # Get unique pincodes
            pincodes = list(set(slot.get('pincode') for slot in slots))
            pincodes.sort()
            
            print(f"\n📍 SERVICEABLE PINCODES ({len(pincodes)}):")
            print("=" * 60)
            
            for pincode in pincodes:
                pincode_slots = [s for s in slots if s.get('pincode') == pincode]
                active_slots = len([s for s in pincode_slots if s.get('isActive', False)])
                total_slots = len(pincode_slots)
                
                print(f"📍 {pincode} - {active_slots}/{total_slots} active slots")
                
        except Exception as e:
            self.print_error(f"Failed to view serviceable pincodes: {str(e)}")

    def _add_serviceable_pincode(self):
        """Add new serviceable pincode"""
        print("\n➕ ADD NEW SERVICEABLE PINCODE")
        print("This will create default delivery slots for the pincode.")
        
        pincode = input("📍 Enter new pincode: ").strip()
        if not pincode or len(pincode) != 6 or not pincode.isdigit():
            self.print_error("Invalid pincode. Must be 6 digits.")
            return
        
        # Check if already exists
        try:
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            if response.get('Items'):
                self.print_error("Pincode already serviceable")
                return
                
        except:
            pass
        
        # Create default slots
        default_slots = [
            {'time': '09:00-12:00', 'type': 'morning', 'capacity': 30, 'charge': 0},
            {'time': '14:00-17:00', 'type': 'afternoon', 'capacity': 25, 'charge': 20},
            {'time': '18:00-21:00', 'type': 'evening', 'charge': 50}
        ]
        
        print(f"\n📋 Creating default slots for pincode {pincode}...")
        
        from decimal import Decimal
        created_count = 0
        
        for slot_info in default_slots:
            try:
                slot_id = f"slot-{pincode}-{slot_info['type']}"
                
                slot_data = {
                    'pincode': pincode,
                    'slotID': slot_id,
                    'timeSlot': slot_info['time'],
                    'slotType': slot_info['type'],
                    'maxOrders': slot_info['capacity'],
                    'currentOrders': 0,
                    'deliveryCharge': Decimal(str(slot_info['charge'])),
                    'isActive': True,
                    'serviceableAreas': [pincode],
                    'slotInfo': {
                        'timeSlot': slot_info['time'],
                        'slotType': slot_info['type'],
                        'maxOrders': slot_info['capacity'],
                        'currentOrders': 0,
                        'deliveryCharge': Decimal(str(slot_info['charge'])),
                        'isActive': True
                    },
                    'createdAt': datetime.now(timezone.utc).isoformat(),
                    'updatedAt': datetime.now(timezone.utc).isoformat(),
                    'createdBy': self.current_user.get('userID', 'system')
                }
                
                self.delivery_table.put_item(Item=slot_data)
                created_count += 1
                print(f"   ✅ Created {slot_info['type']} slot ({slot_info['time']})")
                
            except Exception as e:
                print(f"   ❌ Failed to create {slot_info['type']} slot: {str(e)}")
        
        if created_count > 0:
            self.print_success(f"Pincode {pincode} is now serviceable with {created_count} slots!")
        else:
            self.print_error("Failed to create any slots")

    def _remove_pincode_serviceability(self):
        """Remove pincode serviceability"""
        pincode = input("📍 Enter pincode to remove: ").strip()
        if not pincode:
            self.print_error("Pincode is required")
            return
        
        # Get all slots for this pincode
        try:
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            if not slots:
                self.print_error("Pincode not found or already not serviceable")
                return
            
            # Check for active orders
            active_orders = sum(slot.get('currentOrders', 0) for slot in slots)
            if active_orders > 0:
                print(f"\n⚠️  WARNING: This pincode has {active_orders} active orders!")
                confirm = input("Continue with removal? (y/n): ").strip().lower()
                if confirm != 'y':
                    self.print_info("Removal cancelled")
                    return
            
            # Delete all slots
            deleted_count = 0
            for slot in slots:
                try:
                    self.delivery_table.delete_item(
                        Key={'pincode': pincode, 'slotID': slot['slotID']}
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete slot {slot.get('slotID', 'N/A')}: {str(e)}")
            
            if deleted_count > 0:
                self.print_success(f"Removed serviceability for pincode {pincode} ({deleted_count} slots deleted)")
            else:
                self.print_error("Failed to remove any slots")
                
        except Exception as e:
            self.print_error(f"Failed to remove pincode serviceability: {str(e)}")

    def _check_pincode_status(self):
        """Check pincode serviceability status"""
        pincode = input("📍 Enter pincode to check: ").strip()
        if not pincode:
            self.print_error("Pincode is required")
            return
        
        try:
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            
            if not slots:
                print(f"\n❌ Pincode {pincode} is NOT serviceable")
                return
            
            print(f"\n✅ Pincode {pincode} is SERVICEABLE")
            print("=" * 50)
            
            active_slots = [s for s in slots if s.get('isActive', False)]
            total_capacity = sum(s.get('maxOrders', 0) for s in active_slots)
            current_orders = sum(s.get('currentOrders', 0) for s in slots)
            
            print(f"📊 Total Slots: {len(slots)}")
            print(f"✅ Active Slots: {len(active_slots)}")
            print(f"📦 Total Capacity: {total_capacity} orders/day")
            print(f"📋 Current Orders: {current_orders}")
            print(f"📈 Utilization: {(current_orders/total_capacity*100):.1f}%" if total_capacity > 0 else "📈 Utilization: 0%")
            
            print(f"\n🕒 AVAILABLE TIME SLOTS:")
            for slot in sorted(slots, key=lambda x: x.get('timeSlot', '')):
                time_slot = slot.get('timeSlot', 'N/A')
                slot_type = slot.get('slotType', 'N/A')
                is_active = slot.get('isActive', False)
                delivery_charge = slot.get('deliveryCharge', 0)
                
                status = "✅" if is_active else "❌"
                print(f"   {status} {time_slot} ({slot_type.title()}) - ₹{delivery_charge}")
                
        except Exception as e:
            self.print_error(f"Failed to check pincode status: {str(e)}")

    def slot_utilization_analytics(self):
        """Slot utilization analytics"""
        try:
            self.print_header("SLOT UTILIZATION ANALYTICS")
            
            response = self.delivery_table.scan()
            slots = response.get('Items', [])
            
            if not slots:
                self.print_info("No delivery slots found")
                return
            
            print("📊 SLOT UTILIZATION OVERVIEW:")
            print("=" * 70)
            
            # Overall statistics
            total_slots = len(slots)
            active_slots = len([s for s in slots if s.get('slotInfo', {}).get('isActive', 'false') == 'true'])
            total_capacity = sum(int(s.get('slotInfo', {}).get('maxOrders', 0)) for s in slots if s.get('slotInfo', {}).get('isActive', 'false') == 'true')
            total_orders = sum(int(s.get('slotInfo', {}).get('currentOrders', 0)) for s in slots)
            
            overall_utilization = (total_orders / total_capacity * 100) if total_capacity > 0 else 0
            
            print(f"📋 Total Slots: {total_slots}")
            print(f"✅ Active Slots: {active_slots}")
            print(f"📦 Total Capacity: {total_capacity} orders/day")
            print(f"📋 Current Orders: {total_orders}")
            print(f"📊 Overall Utilization: {overall_utilization:.1f}%")
            
            # Utilization by time slot type
            print(f"\n🕒 UTILIZATION BY TIME SLOT:")
            print("-" * 50)
            
            slot_types = {}
            for slot in slots:
                slot_info = slot.get('slotInfo', {})
                if slot_info.get('isActive', 'false') != 'true':
                    continue
                    
                slot_type = slot_info.get('slotType', 'unknown')
                if slot_type not in slot_types:
                    slot_types[slot_type] = {'capacity': 0, 'orders': 0, 'count': 0}
                
                slot_types[slot_type]['capacity'] += int(slot_info.get('maxOrders', 0))
                slot_types[slot_type]['orders'] += int(slot_info.get('currentOrders', 0))
                slot_types[slot_type]['count'] += 1
            
            for slot_type, stats in sorted(slot_types.items()):
                utilization = (stats['orders'] / stats['capacity'] * 100) if stats['capacity'] > 0 else 0
                emoji = '🌅' if slot_type == 'morning' else '☀️' if slot_type == 'afternoon' else '🌙' if slot_type == 'evening' else '🕒'
                
                print(f"{emoji} {slot_type.title()}: {stats['orders']}/{stats['capacity']} ({utilization:.1f}%) - {stats['count']} slots")
            
            # Top utilized pincodes
            print(f"\n📍 TOP UTILIZED PINCODES:")
            print("-" * 50)
            
            pincode_stats = {}
            for slot in slots:
                if not slot.get('isActive', False):
                    continue
                    
                pincode = slot.get('pincode', 'unknown')
                if pincode not in pincode_stats:
                    pincode_stats[pincode] = {'capacity': 0, 'orders': 0}
                
                pincode_stats[pincode]['capacity'] += slot.get('maxOrders', 0)
                pincode_stats[pincode]['orders'] += slot.get('currentOrders', 0)
            
            # Sort by utilization percentage
            sorted_pincodes = sorted(
                pincode_stats.items(),
                key=lambda x: (x[1]['orders'] / x[1]['capacity']) if x[1]['capacity'] > 0 else 0,
                reverse=True
            )
            
            for pincode, stats in sorted_pincodes[:10]:  # Top 10
                utilization = (stats['orders'] / stats['capacity'] * 100) if stats['capacity'] > 0 else 0
                print(f"📍 {pincode}: {stats['orders']}/{stats['capacity']} ({utilization:.1f}%)")
            
        except Exception as e:
            self.print_error(f"Failed to load slot utilization analytics: {str(e)}")

    def bulk_slot_creation(self):
        """Bulk slot creation for multiple pincodes"""
        try:
            self.print_header("BULK SLOT CREATION")
            
            print("📋 BULK SLOT CREATION OPTIONS:")
            print("-" * 50)
            print("1. 📝 Enter Pincodes Manually")
            print("2. 📄 Import from File")
            print("0. ❌ Cancel")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                self._bulk_create_manual()
            elif choice == '2':
                self._bulk_create_from_file()
            elif choice == '0':
                return
            else:
                self.print_error("Invalid choice")
                
        except Exception as e:
            self.print_error(f"Failed bulk slot creation: {str(e)}")

    def _bulk_create_manual(self):
        """Manual bulk slot creation"""
        print("\n📝 MANUAL BULK CREATION")
        print("Enter pincodes separated by commas (e.g., 500001,500002,500003)")
        
        pincodes_input = input("📍 Enter pincodes: ").strip()
        if not pincodes_input:
            self.print_error("No pincodes entered")
            return
        
        pincodes = [p.strip() for p in pincodes_input.split(',')]
        valid_pincodes = []
        
        # Validate pincodes
        for pincode in pincodes:
            if len(pincode) == 6 and pincode.isdigit():
                valid_pincodes.append(pincode)
            else:
                print(f"⚠️  Skipping invalid pincode: {pincode}")
        
        if not valid_pincodes:
            self.print_error("No valid pincodes found")
            return
        
        print(f"\n✅ Found {len(valid_pincodes)} valid pincodes")
        
        # Create slots for each pincode
        self._create_bulk_slots(valid_pincodes)

    def _bulk_create_from_file(self):
        """Bulk slot creation from file"""
        print("\n📄 IMPORT FROM FILE")
        print("File should contain one pincode per line")
        
        filename = input("📁 Enter filename: ").strip()
        if not filename:
            self.print_error("Filename is required")
            return
        
        try:
            with open(filename, 'r') as file:
                pincodes = [line.strip() for line in file if line.strip()]
            
            valid_pincodes = []
            for pincode in pincodes:
                if len(pincode) == 6 and pincode.isdigit():
                    valid_pincodes.append(pincode)
                else:
                    print(f"⚠️  Skipping invalid pincode: {pincode}")
            
            if not valid_pincodes:
                self.print_error("No valid pincodes found in file")
                return
            
            print(f"\n✅ Found {len(valid_pincodes)} valid pincodes in file")
            self._create_bulk_slots(valid_pincodes)
            
        except FileNotFoundError:
            self.print_error("File not found")
        except Exception as e:
            self.print_error(f"Failed to read file: {str(e)}")

    def _create_bulk_slots(self, pincodes):
        """Create slots for multiple pincodes"""
        from decimal import Decimal
        
        default_slots = [
            {'time': '09:00-12:00', 'type': 'morning', 'capacity': 30, 'charge': 0},
            {'time': '14:00-17:00', 'type': 'afternoon', 'capacity': 25, 'charge': 20},
            {'time': '18:00-21:00', 'type': 'evening', 'capacity': 20, 'charge': 50}
        ]
        
        created_count = 0
        skipped_count = 0
        
        print(f"\n🔄 Creating slots for {len(pincodes)} pincodes...")
        
        for pincode in pincodes:
            # Check if pincode already exists
            try:
                response = self.delivery_table.query(
                    KeyConditionExpression='pincode = :pincode',
                    ExpressionAttributeValues={':pincode': pincode}
                )
                
                if response.get('Items'):
                    print(f"   ⚠️  Skipping {pincode} - already exists")
                    skipped_count += 1
                    continue
                    
            except:
                pass
            
            # Create slots for this pincode
            pincode_created = 0
            for slot_info in default_slots:
                try:
                    slot_id = f"slot-{pincode}-{slot_info['type']}"
                    
                    slot_data = {
                        'pincode': pincode,
                        'slotID': slot_id,
                        'timeSlot': slot_info['time'],
                        'slotType': slot_info['type'],
                        'maxOrders': slot_info['capacity'],
                        'currentOrders': 0,
                        'deliveryCharge': Decimal(str(slot_info['charge'])),
                        'isActive': True,
                        'serviceableAreas': [pincode],
                        'slotInfo': {
                            'timeSlot': slot_info['time'],
                            'slotType': slot_info['type'],
                            'maxOrders': slot_info['capacity'],
                            'currentOrders': 0,
                            'deliveryCharge': Decimal(str(slot_info['charge'])),
                            'isActive': True
                        },
                        'createdAt': datetime.now(timezone.utc).isoformat(),
                        'updatedAt': datetime.now(timezone.utc).isoformat(),
                        'createdBy': self.current_user.get('userID', 'system')
                    }
                    
                    self.delivery_table.put_item(Item=slot_data)
                    pincode_created += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to create {slot_info['type']} slot for {pincode}: {str(e)}")
            
            if pincode_created > 0:
                print(f"   ✅ Created {pincode_created} slots for {pincode}")
                created_count += pincode_created
        
        print(f"\n🎉 BULK CREATION COMPLETE!")
        print(f"✅ Created: {created_count} slots")
        print(f"⚠️  Skipped: {skipped_count} pincodes")

    def search_slots_by_pincode(self):
        """Search slots by pincode"""
        try:
            self.print_header("SEARCH SLOTS BY PINCODE")
            
            pincode = input("📍 Enter pincode to search: ").strip()
            if not pincode:
                self.print_error("Pincode is required")
                return
            
            response = self.delivery_table.query(
                KeyConditionExpression='pincode = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            
            if not slots:
                self.print_error(f"No delivery slots found for pincode {pincode}")
                return
            
            print(f"\n📋 DELIVERY SLOTS FOR PINCODE {pincode}:")
            print("=" * 70)
            
            total_capacity = 0
            total_orders = 0
            
            for slot in sorted(slots, key=lambda x: x.get('timeSlot', '')):
                slot_id = slot.get('slotID', 'N/A')
                time_slot = slot.get('timeSlot', 'N/A')
                slot_type = slot.get('slotType', 'N/A')
                max_orders = slot.get('maxOrders', 0)
                current_orders = slot.get('currentOrders', 0)
                delivery_charge = slot.get('deliveryCharge', 0)
                is_active = slot.get('isActive', False)
                
                status_emoji = "✅" if is_active else "❌"
                utilization = (current_orders / max_orders * 100) if max_orders > 0 else 0
                
                print(f"\n🕒 {time_slot} ({slot_type.title()}) {status_emoji}")
                print(f"   🆔 Slot ID: {slot_id}")
                print(f"   📦 Capacity: {current_orders}/{max_orders} ({utilization:.1f}%)")
                print(f"   💰 Delivery Charge: ₹{delivery_charge}")
                print(f"   📅 Created: {slot.get('createdAt', 'N/A')[:10]}")
                
                if is_active:
                    total_capacity += max_orders
                    total_orders += current_orders
            
            print(f"\n📊 PINCODE SUMMARY:")
            print("-" * 40)
            print(f"📋 Total Slots: {len(slots)}")
            print(f"✅ Active Slots: {len([s for s in slots if s.get('isActive', False)])}")
            print(f"📦 Total Capacity: {total_capacity} orders/day")
            print(f"📋 Current Orders: {total_orders}")
            
            if total_capacity > 0:
                overall_utilization = (total_orders / total_capacity * 100)
                print(f"📊 Overall Utilization: {overall_utilization:.1f}%")
            
        except Exception as e:
            self.print_error(f"Failed to search slots: {str(e)}")

    def slot_performance_report(self):
        """Generate slot performance report"""
        try:
            self.print_header("SLOT PERFORMANCE REPORT")
            
            response = self.delivery_table.scan()
            slots = response.get('Items', [])
            
            if not slots:
                self.print_info("No delivery slots found")
                return
            
            print("📊 COMPREHENSIVE SLOT PERFORMANCE REPORT")
            print("=" * 80)
            
            # Performance metrics
            total_slots = len(slots)
            active_slots = len([s for s in slots if s.get('isActive', False)])
            total_capacity = sum(s.get('maxOrders', 0) for s in slots if s.get('isActive', False))
            total_orders = sum(s.get('currentOrders', 0) for s in slots)
            
            print(f"📈 OVERALL PERFORMANCE:")
            print("-" * 50)
            print(f"📋 Total Slots: {total_slots}")
            print(f"✅ Active Slots: {active_slots} ({(active_slots/total_slots*100):.1f}%)")
            print(f"📦 Total Daily Capacity: {total_capacity} orders")
            print(f"📋 Current Orders: {total_orders}")
            
            if total_capacity > 0:
                utilization = (total_orders / total_capacity * 100)
                print(f"📊 System Utilization: {utilization:.1f}%")
                
                if utilization > 80:
                    print("🔴 HIGH UTILIZATION - Consider adding more slots")
                elif utilization > 60:
                    print("🟡 MODERATE UTILIZATION - Monitor closely")
                else:
                    print("🟢 HEALTHY UTILIZATION - Good capacity")
            
            # Performance by pincode
            print(f"\n📍 PERFORMANCE BY PINCODE:")
            print("-" * 50)
            
            pincode_performance = {}
            for slot in slots:
                pincode = slot.get('pincode', 'unknown')
                if pincode not in pincode_performance:
                    pincode_performance[pincode] = {
                        'slots': 0,
                        'active_slots': 0,
                        'capacity': 0,
                        'orders': 0,
                        'revenue': 0
                    }
                
                stats = pincode_performance[pincode]
                stats['slots'] += 1
                
                if slot.get('isActive', False):
                    stats['active_slots'] += 1
                    stats['capacity'] += slot.get('maxOrders', 0)
                    stats['orders'] += slot.get('currentOrders', 0)
                    stats['revenue'] += float(slot.get('deliveryCharge', 0)) * slot.get('currentOrders', 0)
            
            # Sort by utilization
            sorted_pincodes = sorted(
                pincode_performance.items(),
                key=lambda x: (x[1]['orders'] / x[1]['capacity']) if x[1]['capacity'] > 0 else 0,
                reverse=True
            )
            
            print(f"{'Pincode':<10} {'Util%':<8} {'Orders':<8} {'Capacity':<10} {'Revenue':<10}")
            print("-" * 60)
            
            for pincode, stats in sorted_pincodes[:15]:  # Top 15
                utilization = (stats['orders'] / stats['capacity'] * 100) if stats['capacity'] > 0 else 0
                print(f"{pincode:<10} {utilization:<7.1f}% {stats['orders']:<8} {stats['capacity']:<10} ₹{stats['revenue']:<9.0f}")
            
            # Time slot performance
            print(f"\n🕒 PERFORMANCE BY TIME SLOT:")
            print("-" * 50)
            
            time_performance = {}
            for slot in slots:
                if not slot.get('isActive', False):
                    continue
                    
                slot_type = slot.get('slotType', 'unknown')
                if slot_type not in time_performance:
                    time_performance[slot_type] = {
                        'slots': 0,
                        'capacity': 0,
                        'orders': 0,
                        'revenue': 0
                    }
                
                stats = time_performance[slot_type]
                stats['slots'] += 1
                stats['capacity'] += slot.get('maxOrders', 0)
                stats['orders'] += slot.get('currentOrders', 0)
                stats['revenue'] += float(slot.get('deliveryCharge', 0)) * slot.get('currentOrders', 0)
            
            for slot_type, stats in sorted(time_performance.items()):
                utilization = (stats['orders'] / stats['capacity'] * 100) if stats['capacity'] > 0 else 0
                emoji = '🌅' if slot_type == 'morning' else '☀️' if slot_type == 'afternoon' else '🌙' if slot_type == 'evening' else '🕒'
                
                print(f"{emoji} {slot_type.title():<10} {utilization:<7.1f}% {stats['orders']:<8} {stats['capacity']:<10} ₹{stats['revenue']:<9.0f}")
            
            # Recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            print("-" * 50)
            
            if total_capacity == 0:
                print("🔴 No active slots found - Create delivery slots to start operations")
            elif utilization > 90:
                print("🔴 System overloaded - Urgently add more slots or increase capacity")
            elif utilization > 75:
                print("🟡 High utilization - Consider adding slots for popular pincodes")
            elif utilization < 30:
                print("🔵 Low utilization - Review pricing or marketing strategies")
            else:
                print("🟢 System performing well - Monitor and maintain current capacity")
            
            # Top underperforming pincodes
            underperforming = [
                (pincode, stats) for pincode, stats in pincode_performance.items()
                if stats['capacity'] > 0 and (stats['orders'] / stats['capacity']) < 0.3
            ]
            
            if underperforming:
                print(f"\n⚠️  UNDERPERFORMING PINCODES (< 30% utilization):")
                for pincode, stats in underperforming[:5]:
                    utilization = (stats['orders'] / stats['capacity'] * 100)
                    print(f"   📍 {pincode}: {utilization:.1f}% utilization")
                print("   💡 Consider reducing capacity or improving marketing")
            
        except Exception as e:
            self.print_error(f"Failed to generate performance report: {str(e)}")

    def emergency_operations(self):
        self.print_info("Emergency operations - Coming soon...")

    def add_staff_member(self):
        self.print_info("Add staff member - Coming soon...")

    def staff_performance(self):
        self.print_info("Staff performance - Coming soon...")

    def attendance_management(self):
        self.print_info("Attendance management - Coming soon...")

    def task_assignment(self):
        self.print_info("Task assignment - Coming soon...")

    def performance_reviews(self):
        self.print_info("Performance reviews - Coming soon...")

    def staff_analytics(self):
        self.print_info("Staff analytics - Coming soon...")

    def shift_management(self):
        self.print_info("Shift management - Coming soon...")

    def department_overview(self):
        self.print_info("Department overview - Coming soon...")

    def perform_quality_check(self):
        self.print_info("Perform quality check - Coming soon...")

    def quality_reports(self):
        self.print_info("Quality reports - Coming soon...")

    def temperature_monitoring(self):
        self.print_info("Temperature monitoring - Coming soon...")

    def waste_management(self):
        self.print_info("Waste management - Coming soon...")

    def quality_analytics(self):
        self.print_info("Quality analytics - Coming soon...")

    def quality_standards(self):
        self.print_info("Quality standards - Coming soon...")

    def quality_alerts(self):
        self.print_info("Quality alerts - Coming soon...")

    def order_processing(self):
        """Complete order processing workflow"""
        while True:
            try:
                self.clear_screen()
                self.print_header("ORDER PROCESSING CENTER")
                
                print("📦 ORDER PROCESSING OPTIONS:")
                print("1. 📋 View Pending Orders")
                print("2. 📦 Pack Orders")
                print("3. ✅ Verify Packed Orders")
                print("4. 🚚 Create Delivery Routes")
                print("5. 👤 Assign Riders")
                print("6. 📊 Order Status Tracking")
                print("7. 🚛 Complete Deliveries")
                print("0. ⬅️ Back to Main Menu")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '0':
                    break
                elif choice == '1':
                    self.view_pending_orders()
                elif choice == '2':
                    self.pack_orders()
                elif choice == '3':
                    self.verify_packed_orders()
                elif choice == '4':
                    self.create_delivery_routes()
                elif choice == '5':
                    self.assign_riders()
                elif choice == '6':
                    self.track_order_status()
                elif choice == '7':
                    self.complete_deliveries()
                else:
                    self.print_error("Invalid option")
                    input("Press Enter to continue...")
                    
            except Exception as e:
                self.print_error(f"Order processing error: {str(e)}")
                input("Press Enter to continue...")

    def view_pending_orders(self):
        """View orders pending for processing"""
        try:
            self.print_header("PENDING ORDERS")
            
            # Get orders that need processing
            response = self.orders_table.scan()
            all_orders = response.get('Items', [])
            
            # Filter orders by status
            pending_statuses = ['confirmed', 'processing', 'ready_for_delivery', 'out_for_delivery']
            pending_orders = [order for order in all_orders if order.get('status') in pending_statuses]
            
            if not pending_orders:
                self.print_info("No pending orders found")
                input("Press Enter to continue...")
                return
            
            # Group by status
            status_groups = {}
            for order in pending_orders:
                status = order.get('status')
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(order)
            
            print(f"📦 Found {len(pending_orders)} orders needing attention:")
            print("-" * 80)
            
            for status, orders in status_groups.items():
                print(f"\n📊 {status.upper().replace('_', ' ')} ({len(orders)} orders):")
                for order in orders[:5]:  # Show first 5
                    order_id = order.get('orderID', 'Unknown')[:8]
                    customer_info = order.get('customerInfo', {})
                    customer_name = customer_info.get('name', 'Unknown')
                    total = order.get('orderSummary', {}).get('totalAmount', 0)
                    items_count = len(order.get('items', []))
                    delivery_slot = order.get('deliveryTimeSlot', 'Unknown')
                    pincode = order.get('deliveryPincode', 'Unknown')
                    
                    print(f"   🆔 {order_id}... | 👤 {customer_name} | 💰 ₹{total}")
                    print(f"      📦 {items_count} items | 📍 {pincode} | 🕒 {delivery_slot}")
                
                if len(orders) > 5:
                    print(f"   ... and {len(orders) - 5} more {status} orders")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to view pending orders: {str(e)}")
            input("Press Enter to continue...")

    def pack_orders(self):
        """Pack confirmed orders"""
        try:
            self.print_header("ORDER PACKING")
            
            # Get confirmed orders ready for packing
            response = self.orders_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'confirmed'}
            )
            confirmed_orders = response.get('Items', [])
            
            if not confirmed_orders:
                self.print_info("No confirmed orders to pack")
                input("Press Enter to continue...")
                return
            
            print(f"📦 Found {len(confirmed_orders)} orders ready for packing:")
            print("-" * 80)
            
            for i, order in enumerate(confirmed_orders[:10], 1):
                order_id = order.get('orderID', 'Unknown')[:8]
                customer_info = order.get('customerInfo', {})
                customer_name = customer_info.get('name', 'Unknown')
                items = order.get('items', [])
                
                print(f"\n{i}. Order: {order_id}... - {customer_name}")
                print("   📦 Items to pack:")
                for item in items:
                    print(f"      • {item.get('name', 'Unknown')} - {item.get('quantity', 0)} {item.get('unit', 'units')}")
            
            if len(confirmed_orders) > 10:
                print(f"\n   ... and {len(confirmed_orders) - 10} more orders")
            
            pack_choice = input(f"\nPack all {len(confirmed_orders)} orders? (y/N): ").strip().lower()
            
            if pack_choice == 'y':
                packed_count = 0
                for order in confirmed_orders:
                    try:
                        # Update order status to 'processing' (packed)
                        self.orders_table.update_item(
                            Key={
                                'orderID': order['orderID'],
                                'customerEmail': order['customerEmail']
                            },
                            UpdateExpression='SET #status = :status, updatedAt = :updated, packedAt = :packed, packedBy = :packer',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':status': 'processing',
                                ':updated': datetime.now(timezone.utc).isoformat(),
                                ':packed': datetime.now(timezone.utc).isoformat(),
                                ':packer': self.current_user.get('userID', 'warehouse-staff')
                            }
                        )
                        packed_count += 1
                    except Exception as e:
                        print(f"   ⚠️ Failed to pack order {order.get('orderID', 'Unknown')}: {str(e)}")
                
                self.print_success(f"Successfully packed {packed_count} orders!")
                print(f"📦 Orders are now ready for verification")
            else:
                self.print_info("Packing cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to pack orders: {str(e)}")
            input("Press Enter to continue...")

    def verify_packed_orders(self):
        """Verify packed orders"""
        try:
            self.print_header("ORDER VERIFICATION")
            
            # Get processing orders (packed but not verified)
            response = self.orders_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'processing'}
            )
            processing_orders = response.get('Items', [])
            
            if not processing_orders:
                self.print_info("No packed orders to verify")
                input("Press Enter to continue...")
                return
            
            print(f"✅ Found {len(processing_orders)} packed orders for verification:")
            print("-" * 80)
            
            for i, order in enumerate(processing_orders[:10], 1):
                order_id = order.get('orderID', 'Unknown')[:8]
                customer_info = order.get('customerInfo', {})
                customer_name = customer_info.get('name', 'Unknown')
                packed_at = order.get('packedAt', 'Unknown')[:16].replace('T', ' ')
                items = order.get('items', [])
                
                print(f"\n{i}. Order: {order_id}... - {customer_name}")
                print(f"   📦 Packed at: {packed_at}")
                print(f"   📋 Items ({len(items)}):")
                for item in items[:3]:
                    print(f"      ✅ {item.get('name', 'Unknown')} - {item.get('quantity', 0)} {item.get('unit', 'units')}")
                if len(items) > 3:
                    print(f"      ... and {len(items) - 3} more items")
            
            if len(processing_orders) > 10:
                print(f"\n   ... and {len(processing_orders) - 10} more orders")
            
            verify_choice = input(f"\nVerify all {len(processing_orders)} packed orders? (y/N): ").strip().lower()
            
            if verify_choice == 'y':
                verified_count = 0
                for order in processing_orders:
                    try:
                        # Update order status to 'ready_for_delivery' (verified)
                        self.orders_table.update_item(
                            Key={
                                'orderID': order['orderID'],
                                'customerEmail': order['customerEmail']
                            },
                            UpdateExpression='SET #status = :status, updatedAt = :updated, verifiedAt = :verified, verifiedBy = :verifier',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':status': 'ready_for_delivery',
                                ':updated': datetime.now(timezone.utc).isoformat(),
                                ':verified': datetime.now(timezone.utc).isoformat(),
                                ':verifier': self.current_user.get('userID', 'warehouse-supervisor')
                            }
                        )
                        verified_count += 1
                    except Exception as e:
                        print(f"   ⚠️ Failed to verify order {order.get('orderID', 'Unknown')}: {str(e)}")
                
                self.print_success(f"Successfully verified {verified_count} orders!")
                print(f"✅ Orders are now ready for delivery route creation")
            else:
                self.print_info("Verification cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to verify orders: {str(e)}")
            input("Press Enter to continue...")

    def create_delivery_routes(self):
        """Create delivery routes for ready orders"""
        try:
            self.print_header("CREATE DELIVERY ROUTES")
            
            # Get orders ready for delivery
            response = self.orders_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'ready_for_delivery'}
            )
            ready_orders = response.get('Items', [])
            
            if not ready_orders:
                self.print_info("No orders ready for delivery route creation")
                input("Press Enter to continue...")
                return
            
            # Group orders by pincode for efficient routing
            pincode_groups = {}
            for order in ready_orders:
                pincode = order.get('deliveryPincode', 'Unknown')
                if pincode not in pincode_groups:
                    pincode_groups[pincode] = []
                pincode_groups[pincode].append(order)
            
            print(f"🗺️ Creating routes for {len(ready_orders)} orders across {len(pincode_groups)} areas:")
            print("-" * 80)
            
            for pincode, orders in pincode_groups.items():
                print(f"📍 {pincode}: {len(orders)} orders")
            
            create_routes = input(f"\nCreate delivery routes for all areas? (y/N): ").strip().lower()
            
            if create_routes == 'y':
                route_count = 0
                for pincode, orders in pincode_groups.items():
                    try:
                        # Create route for this pincode
                        route_id = str(uuid.uuid4())
                        route_data = {
                            'routeID': route_id,
                            'vehicleID': f'vehicle-{pincode}',
                            'routeName': f'Route-{pincode}-{datetime.now().strftime("%Y%m%d")}',
                            'pincode': pincode,
                            'orderCount': len(orders),
                            'orderIDs': [order['orderID'] for order in orders],
                            'status': 'planned',
                            'estimatedDuration': len(orders) * 30,  # 30 mins per order
                            'plannedDate': datetime.now(timezone.utc).date().isoformat(),
                            'createdAt': datetime.now(timezone.utc).isoformat(),
                            'createdBy': self.current_user.get('userID', 'warehouse-manager')
                        }
                        
                        # Save route to logistics table
                        self.logistics_table.put_item(Item=route_data)
                        route_count += 1
                        
                        print(f"   ✅ Created route {route_id[:8]}... for {pincode} ({len(orders)} orders)")
                        
                    except Exception as e:
                        print(f"   ⚠️ Failed to create route for {pincode}: {str(e)}")
                
                self.print_success(f"Successfully created {route_count} delivery routes!")
                print(f"🗺️ Routes are ready for rider assignment")
            else:
                self.print_info("Route creation cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to create routes: {str(e)}")
            input("Press Enter to continue...")

    def assign_riders(self):
        """Assign riders to delivery routes"""
        try:
            self.print_header("RIDER ASSIGNMENT")
            
            # Get planned routes
            response = self.logistics_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'planned'}
            )
            planned_routes = response.get('Items', [])
            
            if not planned_routes:
                self.print_info("No planned routes for rider assignment")
                input("Press Enter to continue...")
                return
            
            print(f"🚚 Found {len(planned_routes)} routes ready for rider assignment:")
            print("-" * 80)
            
            # Sample riders (in real system, these would come from staff table)
            available_riders = [
                {'riderID': 'rider-001', 'name': 'Ravi Kumar', 'phone': '+91-9876543001', 'vehicle': 'Bike'},
                {'riderID': 'rider-002', 'name': 'Suresh Reddy', 'phone': '+91-9876543002', 'vehicle': 'Bike'},
                {'riderID': 'rider-003', 'name': 'Amit Singh', 'phone': '+91-9876543003', 'vehicle': 'Van'},
                {'riderID': 'rider-004', 'name': 'Priya Sharma', 'phone': '+91-9876543004', 'vehicle': 'Bike'},
                {'riderID': 'rider-005', 'name': 'Kiran Patel', 'phone': '+91-9876543005', 'vehicle': 'Van'}
            ]
            
            for i, route in enumerate(planned_routes[:10], 1):
                route_id = route.get('routeID', 'Unknown')[:8]
                pincode = route.get('pincode', 'Unknown')
                order_count = route.get('orderCount', 0)
                
                print(f"\n{i}. Route: {route_id}... - {pincode}")
                print(f"   📦 Orders: {order_count}")
                print(f"   🕒 Est. Duration: {route.get('estimatedDuration', 0)} minutes")
            
            assign_choice = input(f"\nAssign riders to all {len(planned_routes)} routes? (y/N): ").strip().lower()
            
            if assign_choice == 'y':
                assigned_count = 0
                for i, route in enumerate(planned_routes):
                    try:
                        # Assign rider (cycling through available riders)
                        rider = available_riders[i % len(available_riders)]
                        
                        # Update route with rider assignment
                        self.logistics_table.update_item(
                            Key={
                                'routeID': route['routeID'],
                                'vehicleID': route['vehicleID']
                            },
                            UpdateExpression='SET #status = :status, updatedAt = :updated, assignedRider = :rider, assignedAt = :assigned',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':status': 'assigned',
                                ':updated': datetime.now(timezone.utc).isoformat(),
                                ':rider': rider,
                                ':assigned': datetime.now(timezone.utc).isoformat()
                            }
                        )
                        
                        # Update all orders in this route to 'out_for_delivery'
                        for order_id in route.get('orderIDs', []):
                            # Find the order to get customerEmail
                            order_response = self.orders_table.scan(
                                FilterExpression='orderID = :order_id',
                                ExpressionAttributeValues={':order_id': order_id}
                            )
                            orders = order_response.get('Items', [])
                            if orders:
                                order = orders[0]
                                self.orders_table.update_item(
                                    Key={
                                        'orderID': order['orderID'],
                                        'customerEmail': order['customerEmail']
                                    },
                                    UpdateExpression='SET #status = :status, updatedAt = :updated, assignedRider = :rider, routeID = :route_id',
                                    ExpressionAttributeNames={'#status': 'status'},
                                    ExpressionAttributeValues={
                                        ':status': 'out_for_delivery',
                                        ':updated': datetime.now(timezone.utc).isoformat(),
                                        ':rider': rider,
                                        ':route_id': route['routeID']
                                    }
                                )
                        
                        assigned_count += 1
                        print(f"   ✅ Assigned {rider['name']} ({rider['vehicle']}) to route {route['routeID'][:8]}...")
                        
                    except Exception as e:
                        print(f"   ⚠️ Failed to assign rider to route {route.get('routeID', 'Unknown')}: {str(e)}")
                
                self.print_success(f"Successfully assigned riders to {assigned_count} routes!")
                print(f"🚚 Orders are now out for delivery")
            else:
                self.print_info("Rider assignment cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to assign riders: {str(e)}")
            input("Press Enter to continue...")

    def track_order_status(self):
        """Track order status across the workflow"""
        try:
            self.print_header("ORDER STATUS TRACKING")
            
            # Get all orders and show status distribution
            response = self.orders_table.scan()
            all_orders = response.get('Items', [])
            
            if not all_orders:
                self.print_info("No orders found")
                input("Press Enter to continue...")
                return
            
            # Count by status
            status_counts = {}
            total_revenue = Decimal('0')
            
            for order in all_orders:
                status = order.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Add to total revenue
                if 'orderSummary' in order:
                    amount = Decimal(str(order['orderSummary'].get('totalAmount', 0)))
                    total_revenue += amount
            
            print("📊 ORDER STATUS DASHBOARD:")
            print("-" * 60)
            
            status_icons = {
                'confirmed': '🔄',
                'processing': '📦',
                'ready_for_delivery': '✅',
                'out_for_delivery': '🚚',
                'delivered': '🎉',
                'cancelled': '❌'
            }
            
            for status, count in status_counts.items():
                icon = status_icons.get(status, '📋')
                percentage = (count / len(all_orders)) * 100
                print(f"{icon} {status.upper().replace('_', ' ')}: {count} orders ({percentage:.1f}%)")
            
            print(f"\n💰 FINANCIAL OVERVIEW:")
            print(f"   Total Orders: {len(all_orders)}")
            print(f"   Total Revenue: ₹{total_revenue:,.2f}")
            
            # Show recent activity
            print(f"\n🕒 RECENT ORDER ACTIVITY:")
            recent_orders = sorted(all_orders, key=lambda x: x.get('updatedAt', ''), reverse=True)[:5]
            
            for order in recent_orders:
                order_id = order.get('orderID', 'Unknown')[:8]
                status = order.get('status', 'unknown')
                updated = order.get('updatedAt', '')[:16].replace('T', ' ')
                customer_name = order.get('customerInfo', {}).get('name', 'Unknown')
                
                print(f"   {status_icons.get(status, '📋')} {order_id}... - {customer_name} - {status} ({updated})")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to track orders: {str(e)}")
            input("Press Enter to continue...")

    def complete_deliveries(self):
        """Complete deliveries and mark orders as delivered"""
        try:
            self.print_header("COMPLETE DELIVERIES")
            
            # Get orders out for delivery
            response = self.orders_table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'out_for_delivery'}
            )
            delivery_orders = response.get('Items', [])
            
            if not delivery_orders:
                self.print_info("No orders out for delivery")
                input("Press Enter to continue...")
                return
            
            print(f"🚛 Found {len(delivery_orders)} orders out for delivery:")
            print("-" * 80)
            
            # Group by rider
            rider_groups = {}
            for order in delivery_orders:
                rider_info = order.get('assignedRider', {})
                rider_name = rider_info.get('name', 'Unassigned')
                if rider_name not in rider_groups:
                    rider_groups[rider_name] = []
                rider_groups[rider_name].append(order)
            
            for rider_name, orders in rider_groups.items():
                print(f"\n🚴 {rider_name}: {len(orders)} orders")
                for order in orders[:3]:
                    order_id = order.get('orderID', 'Unknown')[:8]
                    customer_name = order.get('customerInfo', {}).get('name', 'Unknown')
                    pincode = order.get('deliveryPincode', 'Unknown')
                    print(f"   📦 {order_id}... - {customer_name} ({pincode})")
                
                if len(orders) > 3:
                    print(f"   ... and {len(orders) - 3} more orders")
            
            # Complete some deliveries
            complete_choice = input(f"\nMark some orders as delivered? (y/N): ").strip().lower()
            
            if complete_choice == 'y':
                # Complete 60% of out for delivery orders
                orders_to_complete = delivery_orders[:int(len(delivery_orders) * 0.6)]
                completed_count = 0
                
                for order in orders_to_complete:
                    try:
                        self.orders_table.update_item(
                            Key={
                                'orderID': order['orderID'],
                                'customerEmail': order['customerEmail']
                            },
                            UpdateExpression='SET #status = :status, updatedAt = :updated, deliveredAt = :delivered',
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':status': 'delivered',
                                ':updated': datetime.now(timezone.utc).isoformat(),
                                ':delivered': datetime.now(timezone.utc).isoformat()
                            }
                        )
                        completed_count += 1
                    except Exception as e:
                        print(f"   ⚠️ Failed to complete delivery for {order.get('orderID', 'Unknown')}: {str(e)}")
                
                self.print_success(f"Successfully completed {completed_count} deliveries!")
                print(f"🎉 Orders are now marked as delivered")
            else:
                self.print_info("Delivery completion cancelled")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to complete deliveries: {str(e)}")
            input("Press Enter to continue...")

    def analytics_reports(self):
        self.print_info("Analytics & reports - Coming soon...")

    def warehouse_settings(self):
        self.print_info("Warehouse settings - Coming soon...")

    def logout(self):
        """Logout current user"""
        self.print_success("Logged out successfully")
        print("👋 Thank you for using Aurora Spark Theme Warehouse Manager Portal!")
        self.current_user = None

    def run(self):
        """Main application entry point"""
        self.clear_screen()
        self.print_header("AUTHENTICATION")
        
        print("🏭 Welcome to Aurora Spark Theme Warehouse Manager Portal")
        print("Combined: Warehouse + Logistics + Inventory Operations")
        print()
        print("🔐 Please authenticate to access the system")
        print("⚠️  Warehouse operations credentials required")
        print()
        print("🔑 DEFAULT TEST CREDENTIALS:")
        print("   📧 Email: warehouse@promodeagro.com")
        print("   🔒 Password: password123")
        print("   📧 Email: logistics@promodeagro.com") 
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
        print("🏭 Starting Aurora Spark Theme Warehouse Manager Portal...")
        print("=" * 70)
        
        portal = WarehouseManagerPortal()
        portal.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 Warehouse Manager Portal terminated by user")
        print("Thank you for using Aurora Spark Theme!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error in Warehouse Manager Portal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
