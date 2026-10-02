#!/usr/bin/env python3
# customer_portal.py
"""
Customer Portal
Complete customer functionality: Product browsing, cart management, address management, 
slot selection, and order placement
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


class CustomerPortal:
    """E-commerce Customer Portal - Complete Shopping Experience"""
    
    def __init__(self):
        self.region_name = 'ap-south-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Aurora Spark Theme Optimized Tables
        self.users_table = self.dynamodb.Table('AuroraSparkTheme-Users')
        self.products_table = self.dynamodb.Table('AuroraSparkTheme-Products')
        self.inventory_table = self.dynamodb.Table('AuroraSparkTheme-Inventory')
        self.orders_table = self.dynamodb.Table('AuroraSparkTheme-Orders')
        self.delivery_table = self.dynamodb.Table('AuroraSparkTheme-Delivery')
        self.system_table = self.dynamodb.Table('AuroraSparkTheme-System')
        
        self.current_user = None
        self.cart = []
        self.selected_address = None
        self.selected_slot = None
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 100)
        print(f"🛒 [E-COMMERCE - CUSTOMER PORTAL] {title}")
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
    
    def get_product_price(self, product: Dict[str, Any]) -> float:
        """Get product price, handling missing pricing data"""
        pricing = product.get('pricing', {})
        price = pricing.get('sellingPrice', 0)
        
        # If no price at product level, try to get from first variant
        if not price and product.get('hasVariants') and product.get('variants'):
            variants = product.get('variants', [])
            if variants:
                first_variant = variants[0]
                variant_pricing = first_variant.get('pricing', {})
                price = variant_pricing.get('sellingPrice', 0)
        
        return float(price) if price else 0.0
    
    def get_simulated_stock(self, inventory: Dict[str, Any], is_variant: bool = False) -> int:
        """Get simulated stock level"""
        if is_variant:
            # For variants, simulate based on trackInventory
            if inventory.get('trackInventory', False):
                return 50  # Simulate 50 units for variants
            else:
                return 0
        else:
            # For products, simulate based on maxStock
            min_stock = inventory.get('minStock', 0)
            max_stock = inventory.get('maxStock', 0)
            if inventory.get('trackInventory', False) and max_stock:
                return int(float(max_stock) * 0.7)
            else:
                return 0
    
    def authenticate_user(self, email: str, password: str) -> bool:
        """Authenticate customer user"""
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
            
            # Check if user has customer role
            user_roles = user.get('roles', [])
            if 'customer' not in [role.get('name', '').lower() for role in user_roles]:
                self.print_error("Access denied: Customer role required")
                return False
                
            self.current_user = user
            self.print_success(f"Welcome, {user.get('firstName', '')} {user.get('lastName', '')}!")
            return True
            
        except Exception as e:
            self.print_error(f"Authentication failed: {str(e)}")
            return False

    def register_customer(self):
        """Register new customer"""
        try:
            self.print_header("CUSTOMER REGISTRATION")
            
            # Get user details
            first_name = input("First Name: ").strip()
            last_name = input("Last Name: ").strip()
            email = input("Email: ").strip()
            phone = input("Phone: ").strip()
            password = getpass.getpass("Password: ")
            confirm_password = getpass.getpass("Confirm Password: ")
            
            if not all([first_name, last_name, email, phone, password]):
                self.print_error("All fields are required")
                return False
                
            if password != confirm_password:
                self.print_error("Passwords do not match")
                return False
            
            # Check if email already exists
            response = self.users_table.query(
                IndexName='EmailIndex',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if response.get('Items'):
                self.print_error("Email already registered")
                return False
            
            # Create customer user
            user_id = str(uuid.uuid4())
            user_data = {
                'userID': user_id,
                'email': email,
                'passwordHash': self.hash_password(password),
                'firstName': first_name,
                'lastName': last_name,
                'phone': phone,
                'status': 'active',
                'emailVerified': False,
                'roles': [
                    {
                        'roleID': 'role-customer',
                        'name': 'customer',
                        'permissions': ['browse_products', 'place_orders', 'manage_cart', 'manage_addresses']
                    }
                ],
                'addresses': [],
                'preferences': {
                    'notifications': True,
                    'marketing': False
                },
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            self.users_table.put_item(Item=user_data)
            self.print_success("Customer registration successful!")
            
            # Automatically log in the user
            self.current_user = user_data
            self.print_success(f"Welcome to E-commerce Store, {first_name}!")
            input("\nPress Enter to continue to the main menu...")
            return True
            
        except Exception as e:
            self.print_error(f"Registration failed: {str(e)}")
            return False

    def list_categories(self):
        """List all product categories"""
        try:
            self.print_header("PRODUCT CATEGORIES")
            
            # Get all products to extract categories
            response = self.products_table.scan()
            products = response.get('Items', [])
            
            # Extract unique categories
            categories = {}
            for product in products:
                if product.get('status') == 'active' and product.get('isB2cAvailable', True):
                    category = product.get('category', 'uncategorized')
                    if category not in categories:
                        categories[category] = {
                            'name': category.title(),
                            'count': 0,
                            'description': f"{category.title()} products"
                        }
                    categories[category]['count'] += 1
            
            if not categories:
                self.print_info("No categories available")
                return []
            
            print("\n📂 Available Categories:")
            print("-" * 60)
            for i, (cat_key, cat_data) in enumerate(categories.items(), 1):
                print(f"{i:2d}. {cat_data['name']:<20} ({cat_data['count']} products)")
            
            return list(categories.keys())
            
        except Exception as e:
            self.print_error(f"Failed to load categories: {str(e)}")
            return []

    def list_products(self, category: str = None, search_term: str = None):
        """List products with optional category filter and search"""
        try:
            self.print_header("PRODUCT CATALOG")
            
            # Get products
            if category:
                response = self.products_table.query(
                    IndexName='CategoryIndex',
                    KeyConditionExpression='category = :category',
                    ExpressionAttributeValues={':category': category}
                )
            else:
                response = self.products_table.scan()
            
            products = response.get('Items', [])
            
            # Filter active and B2C available products
            available_products = []
            for product in products:
                if (product.get('status') == 'active' and 
                    product.get('isActive', True)):
                    
                    # Apply search filter if provided
                    if search_term:
                        search_term_lower = search_term.lower()
                        if (search_term_lower not in product.get('name', '').lower() and
                            search_term_lower not in product.get('description', '').lower()):
                            continue
                    
                    available_products.append(product)
            
            if not available_products:
                self.print_info("No products found")
                return []
            
            # Display products
            print(f"\n🛍️  Available Products ({len(available_products)} items):")
            print("-" * 100)
            
            for i, product in enumerate(available_products, 1):
                name = product.get('name', 'Unknown')
                price = self.get_product_price(product)
                unit = product.get('unit', 'piece')
                description = product.get('description', '')[:50] + '...' if len(product.get('description', '')) > 50 else product.get('description', '')
                inventory = product.get('inventory', {})
                current_stock = self.get_simulated_stock(inventory)
                stock_status = "In Stock" if current_stock > 0 else "Out of Stock"
                
                print(f"{i:2d}. {name:<25} | ₹{price}/{unit} | {stock_status}")
                print(f"    📝 {description}")
                
                # Show variants if available
                if product.get('hasVariants') and product.get('variants'):
                    variants = product.get('variants', [])
                    variant_info = []
                    for variant in variants[:3]:  # Show first 3 variants
                        attributes = variant.get('attributes', {})
                        variant_name = variant.get('variantName', 'Unknown')
                        variant_price = variant.get('pricing', {}).get('sellingPrice', price)
                        variant_info.append(f"{variant_name}: ₹{variant_price}")
                    if variant_info:
                        print(f"    🔄 Variants: {', '.join(variant_info)}")
                        if len(variants) > 3:
                            print(f"    ... and {len(variants) - 3} more variants")
                
                print()
            
            return available_products
            
        except Exception as e:
            self.print_error(f"Failed to load products: {str(e)}")
            return []

    def view_product_details(self, product_id: str):
        """View detailed product information"""
        try:
            # Since we need both productID and category for the key, scan for the product
            response = self.products_table.scan(
                FilterExpression='productID = :product_id',
                ExpressionAttributeValues={':product_id': product_id}
            )
            products = response.get('Items', [])
            product = products[0] if products else None
            
            if not product:
                self.print_error("Product not found")
                return None
            
            self.print_header("PRODUCT DETAILS")
            
            price = self.get_product_price(product)
            inventory = product.get('inventory', {})
            current_stock = self.get_simulated_stock(inventory)
            
            print(f"📦 Product: {product.get('name', 'Unknown')}")
            print(f"🏷️  Code: {product.get('productCode', 'N/A')}")
            print(f"📂 Category: {product.get('category', 'N/A').title()}")
            print(f"💰 Price: ₹{price}/{product.get('unit', 'piece')}")
            print(f"📊 Stock: {current_stock} {product.get('unit', 'pieces')} available")
            print(f"📝 Description: {product.get('description', 'No description available')}")
            
            # Quality information
            if product.get('qualityGrade'):
                print(f"⭐ Quality: {product.get('qualityGrade', 'N/A').title()}")
            
            # Storage and freshness info
            if product.get('perishable'):
                shelf_life = product.get('shelfLifeDays', 'N/A')
                print(f"🕒 Shelf Life: {shelf_life} days")
                
                storage_req = product.get('storageRequirements', {})
                if storage_req:
                    temp_min = storage_req.get('temperatureMin')
                    temp_max = storage_req.get('temperatureMax')
                    if temp_min and temp_max:
                        print(f"🌡️  Storage: {temp_min}°C to {temp_max}°C")
            
            # Variants
            if product.get('hasVariants') and product.get('variants'):
                print("\n🔄 Available Variants:")
                variants = product.get('variants', [])
                for variant in variants:
                    variant_name = variant.get('variantName', 'Unknown')
                    variant_pricing = variant.get('pricing', {})
                    variant_price = variant_pricing.get('sellingPrice', price)
                    variant_inventory = variant.get('inventory', {})
                    # Simulate variant stock
                    if variant_inventory.get('trackInventory', False):
                        variant_stock = 50  # Simulate 50 units for variants
                    else:
                        variant_stock = 0
                    attributes = variant.get('attributes', {})
                    attr_str = ', '.join([f"{k}: {v}" for k, v in attributes.items()])
                    print(f"   • {variant_name} ({attr_str}) - ₹{variant_price} ({variant_stock} available)")
            
            return product
            
        except Exception as e:
            self.print_error(f"Failed to load product details: {str(e)}")
            return None

    def search_products(self):
        """Search products by name or description"""
        try:
            self.print_header("PRODUCT SEARCH")
            
            search_term = input("Enter search term: ").strip()
            if not search_term:
                self.print_error("Please enter a search term")
                return
            
            products = self.list_products(search_term=search_term)
            
            if products:
                print(f"\n🔍 Found {len(products)} products matching '{search_term}'")
            
        except Exception as e:
            self.print_error(f"Search failed: {str(e)}")

    def add_to_cart(self, product_id: str, quantity: int = 1, variant_id: str = None):
        """Add product to cart"""
        try:
            # Get product details (scan since we need productID + category key)
            response = self.products_table.scan(
                FilterExpression='productID = :product_id',
                ExpressionAttributeValues={':product_id': product_id}
            )
            products = response.get('Items', [])
            product = products[0] if products else None
            
            if not product:
                self.print_error("Product not found")
                return False
            
            if product.get('status') != 'active' or not product.get('isActive', True):
                self.print_error("Product is not available for purchase")
                return False
            
            # Check stock (simulate since currentStock doesn't exist)
            inventory = product.get('inventory', {})
            min_stock = inventory.get('minStock', 0)
            max_stock = inventory.get('maxStock', 0)
            if inventory.get('trackInventory', False) and max_stock:
                available_stock = int(float(max_stock) * 0.7)
            else:
                available_stock = 0
            
            selected_variant = None
            
            if variant_id and product.get('hasVariants'):
                # Find variant stock
                variants = product.get('variants', [])
                variant = next((v for v in variants if v.get('variantID') == variant_id), None)
                if variant:
                    variant_inventory = variant.get('inventory', {})
                    # Simulate variant stock
                    if variant_inventory.get('trackInventory', False):
                        available_stock = 50  # Simulate 50 units for variants
                    else:
                        available_stock = 0
                    selected_variant = variant
                else:
                    self.print_error("Variant not found")
                    return False
            
            if available_stock < quantity:
                self.print_error(f"Insufficient stock. Only {available_stock} available")
                return False
            
            # Check if item already in cart
            cart_item = None
            for item in self.cart:
                if (item['product_id'] == product_id and 
                    item.get('variant_id') == variant_id):
                    cart_item = item
                    break
            
            if cart_item:
                # Update quantity
                new_quantity = cart_item['quantity'] + quantity
                if new_quantity > available_stock:
                    self.print_error(f"Cannot add {quantity} more. Total would exceed available stock ({available_stock})")
                    return False
                cart_item['quantity'] = new_quantity
            else:
                # Add new item
                pricing = product.get('pricing', {})
                price = pricing.get('sellingPrice', 0)
                variant_name = product.get('name', 'Unknown')
                
                if selected_variant:
                    variant_pricing = selected_variant.get('pricing', {})
                    price = variant_pricing.get('sellingPrice', price)
                    variant_name = selected_variant.get('variantName', variant_name)
                
                cart_item = {
                    'product_id': product_id,
                    'variant_id': variant_id,
                    'name': variant_name,
                    'price': price,
                    'quantity': quantity,
                    'unit': product.get('unit', 'piece'),
                    'total': Decimal(str(price)) * quantity
                }
                self.cart.append(cart_item)
            
            # Update total
            cart_item['total'] = Decimal(str(cart_item['price'])) * cart_item['quantity']
            
            self.print_success(f"Added {quantity} x {product.get('name')} to cart")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to add to cart: {str(e)}")
            return False

    def view_cart(self):
        """View current cart contents"""
        try:
            self.print_header("SHOPPING CART")
            
            if not self.cart:
                self.print_info("Your cart is empty")
                return
            
            print("\n🛒 Cart Contents:")
            print("-" * 80)
            
            total_amount = Decimal('0')
            for i, item in enumerate(self.cart, 1):
                name = item['name']
                quantity = item['quantity']
                price = item['price']
                unit = item['unit']
                item_total = item['total']
                
                print(f"{i:2d}. {name:<30} | {quantity} {unit} × ₹{price} = ₹{item_total}")
                
                if item.get('variant_id'):
                    print(f"    🔄 Variant: {item.get('variant_id')}")
                
                total_amount += Decimal(str(item_total))
            
            print("-" * 80)
            print(f"💰 Total Amount: ₹{total_amount}")
            print(f"📦 Total Items: {len(self.cart)}")
            
        except Exception as e:
            self.print_error(f"Failed to display cart: {str(e)}")

    def remove_from_cart(self, item_index: int):
        """Remove item from cart"""
        try:
            if not self.cart:
                self.print_error("Cart is empty")
                return False
            
            if item_index < 1 or item_index > len(self.cart):
                self.print_error("Invalid item number")
                return False
            
            removed_item = self.cart.pop(item_index - 1)
            self.print_success(f"Removed {removed_item['name']} from cart")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to remove item: {str(e)}")
            return False

    def update_cart_quantity(self, item_index: int, new_quantity: int):
        """Update quantity of item in cart"""
        try:
            if not self.cart:
                self.print_error("Cart is empty")
                return False
            
            if item_index < 1 or item_index > len(self.cart):
                self.print_error("Invalid item number")
                return False
            
            if new_quantity <= 0:
                return self.remove_from_cart(item_index)
            
            item = self.cart[item_index - 1]
            
            # Check stock availability (scan since we need productID + category key)
            response = self.products_table.scan(
                FilterExpression='productID = :product_id',
                ExpressionAttributeValues={':product_id': item['product_id']}
            )
            products = response.get('Items', [])
            product = products[0] if products else None
            
            if not product:
                self.print_error("Product not found")
                return False
            
            inventory = product.get('inventory', {})
            # Simulate stock
            min_stock = inventory.get('minStock', 0)
            max_stock = inventory.get('maxStock', 0)
            if inventory.get('trackInventory', False) and max_stock:
                available_stock = int(float(max_stock) * 0.7)
            else:
                available_stock = 0
            
            if item.get('variant_id') and product.get('hasVariants'):
                variants = product.get('variants', [])
                variant = next((v for v in variants if v.get('variantID') == item['variant_id']), None)
                if variant:
                    variant_inventory = variant.get('inventory', {})
                    # Simulate variant stock
                    if variant_inventory.get('trackInventory', False):
                        available_stock = 50
                    else:
                        available_stock = 0
            
            if new_quantity > available_stock:
                self.print_error(f"Insufficient stock. Only {available_stock} available")
                return False
            
            item['quantity'] = new_quantity
            item['total'] = Decimal(str(item['price'])) * new_quantity
            
            self.print_success(f"Updated quantity to {new_quantity}")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to update quantity: {str(e)}")
            return False

    def manage_addresses(self):
        """Manage customer addresses"""
        try:
            if not self.require_authentication():
                return
                
            self.print_header("ADDRESS MANAGEMENT")
            
            addresses = self.current_user.get('addresses', [])
            
            while True:
                print("\n📍 Address Management:")
                print("1. View Addresses")
                print("2. Add New Address")
                print("3. Edit Address")
                print("4. Delete Address")
                print("5. Set Default Address")
                print("6. Back to Main Menu")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self.view_addresses()
                elif choice == '2':
                    self.add_address()
                elif choice == '3':
                    self.edit_address()
                elif choice == '4':
                    self.delete_address()
                elif choice == '5':
                    self.set_default_address()
                elif choice == '6':
                    break
                else:
                    self.print_error("Invalid option")
                    
        except Exception as e:
            self.print_error(f"Address management failed: {str(e)}")

    def view_addresses(self):
        """View all customer addresses"""
        try:
            addresses = self.current_user.get('addresses', [])
            
            if not addresses:
                self.print_info("No addresses found")
                return
            
            print("\n🏠 Your Addresses:")
            print("-" * 80)
            
            for i, address in enumerate(addresses, 1):
                is_default = address.get('isDefault', False)
                default_text = " (Default)" if is_default else ""
                
                print(f"{i:2d}. {address.get('type', 'Home').title()} Address{default_text}")
                print(f"    📍 {address.get('addressLine1', '')}")
                if address.get('addressLine2'):
                    print(f"       {address.get('addressLine2', '')}")
                print(f"       {address.get('city', '')}, {address.get('state', '')} - {address.get('pincode', '')}")
                if address.get('landmark'):
                    print(f"    🏛️  Landmark: {address.get('landmark', '')}")
                print()
                
        except Exception as e:
            self.print_error(f"Failed to display addresses: {str(e)}")

    def add_address(self):
        """Add new address"""
        try:
            self.print_header("ADD NEW ADDRESS")
            
            # Get address details
            address_type = input("Address Type (home/work/other): ").strip().lower() or 'home'
            address_line1 = input("Address Line 1: ").strip()
            address_line2 = input("Address Line 2 (optional): ").strip()
            city = input("City: ").strip()
            state = input("State: ").strip()
            pincode = input("Pincode: ").strip()
            landmark = input("Landmark (optional): ").strip()
            
            if not all([address_line1, city, state, pincode]):
                self.print_error("Required fields: Address Line 1, City, State, Pincode")
                return False
            
            # Validate pincode
            if not pincode.isdigit() or len(pincode) != 6:
                self.print_error("Invalid pincode format")
                return False
            
            # Check if this is the first address (make it default)
            addresses = self.current_user.get('addresses', [])
            is_default = len(addresses) == 0
            
            new_address = {
                'id': str(uuid.uuid4()),
                'type': address_type,
                'addressLine1': address_line1,
                'addressLine2': address_line2,
                'city': city,
                'state': state,
                'pincode': pincode,
                'landmark': landmark,
                'isDefault': is_default,
                'createdAt': datetime.now(timezone.utc).isoformat()
            }
            
            addresses.append(new_address)
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET addresses = :addresses, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':addresses': addresses,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['addresses'] = addresses
            
            self.print_success("Address added successfully!")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to add address: {str(e)}")
            return False

    def edit_address(self):
        """Edit existing address"""
        try:
            addresses = self.current_user.get('addresses', [])
            
            if not addresses:
                self.print_info("No addresses to edit")
                return False
            
            self.view_addresses()
            
            try:
                index = int(input("\nEnter address number to edit: ")) - 1
                if index < 0 or index >= len(addresses):
                    self.print_error("Invalid address number")
                    return False
            except ValueError:
                self.print_error("Invalid input")
                return False
            
            address = addresses[index]
            
            print(f"\nEditing {address.get('type', 'Home').title()} Address:")
            print("(Press Enter to keep current value)")
            
            # Update fields
            new_type = input(f"Address Type ({address.get('type', 'home')}): ").strip()
            if new_type:
                address['type'] = new_type.lower()
            
            new_line1 = input(f"Address Line 1 ({address.get('addressLine1', '')}): ").strip()
            if new_line1:
                address['addressLine1'] = new_line1
            
            new_line2 = input(f"Address Line 2 ({address.get('addressLine2', '')}): ").strip()
            if new_line2 or new_line2 == '':
                address['addressLine2'] = new_line2
            
            new_city = input(f"City ({address.get('city', '')}): ").strip()
            if new_city:
                address['city'] = new_city
            
            new_state = input(f"State ({address.get('state', '')}): ").strip()
            if new_state:
                address['state'] = new_state
            
            new_pincode = input(f"Pincode ({address.get('pincode', '')}): ").strip()
            if new_pincode:
                if not new_pincode.isdigit() or len(new_pincode) != 6:
                    self.print_error("Invalid pincode format")
                    return False
                address['pincode'] = new_pincode
            
            new_landmark = input(f"Landmark ({address.get('landmark', '')}): ").strip()
            if new_landmark or new_landmark == '':
                address['landmark'] = new_landmark
            
            address['updatedAt'] = datetime.now(timezone.utc).isoformat()
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET addresses = :addresses, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':addresses': addresses,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['addresses'] = addresses
            
            self.print_success("Address updated successfully!")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to edit address: {str(e)}")
            return False

    def delete_address(self):
        """Delete address"""
        try:
            addresses = self.current_user.get('addresses', [])
            
            if not addresses:
                self.print_info("No addresses to delete")
                return False
            
            self.view_addresses()
            
            try:
                index = int(input("\nEnter address number to delete: ")) - 1
                if index < 0 or index >= len(addresses):
                    self.print_error("Invalid address number")
                    return False
            except ValueError:
                self.print_error("Invalid input")
                return False
            
            address = addresses[index]
            
            # Confirm deletion
            confirm = input(f"Delete {address.get('type', 'Home').title()} address? (y/N): ").strip().lower()
            if confirm != 'y':
                self.print_info("Deletion cancelled")
                return False
            
            # If deleting default address, make another one default
            was_default = address.get('isDefault', False)
            addresses.pop(index)
            
            if was_default and addresses:
                addresses[0]['isDefault'] = True
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET addresses = :addresses, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':addresses': addresses,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['addresses'] = addresses
            
            self.print_success("Address deleted successfully!")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to delete address: {str(e)}")
            return False

    def set_default_address(self):
        """Set default address"""
        try:
            addresses = self.current_user.get('addresses', [])
            
            if not addresses:
                self.print_info("No addresses available")
                return False
            
            self.view_addresses()
            
            try:
                index = int(input("\nEnter address number to set as default: ")) - 1
                if index < 0 or index >= len(addresses):
                    self.print_error("Invalid address number")
                    return False
            except ValueError:
                self.print_error("Invalid input")
                return False
            
            # Update default flags
            for i, addr in enumerate(addresses):
                addr['isDefault'] = (i == index)
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET addresses = :addresses, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':addresses': addresses,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['addresses'] = addresses
            
            self.print_success("Default address updated successfully!")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to set default address: {str(e)}")
            return False

    def select_delivery_address(self):
        """Select delivery address for order"""
        try:
            addresses = self.current_user.get('addresses', [])
            
            if not addresses:
                self.print_error("No addresses available. Please add an address first.")
                return None
            
            self.print_header("SELECT DELIVERY ADDRESS")
            self.view_addresses()
            
            try:
                index = int(input("\nEnter address number for delivery: ")) - 1
                if index < 0 or index >= len(addresses):
                    self.print_error("Invalid address number")
                    return None
            except ValueError:
                self.print_error("Invalid input")
                return None
            
            selected_address = addresses[index]
            self.selected_address = selected_address
            
            self.print_success(f"Selected {selected_address.get('type', 'Home').title()} address for delivery")
            return selected_address
            
        except Exception as e:
            self.print_error(f"Failed to select address: {str(e)}")
            return None

    def get_available_slots(self, pincode: str):
        """Get available delivery slots for pincode"""
        try:
            # Query delivery slots by pincodeID (more efficient than scan)
            response = self.delivery_table.query(
                KeyConditionExpression='pincodeID = :pincode',
                ExpressionAttributeValues={':pincode': pincode}
            )
            
            slots = response.get('Items', [])
            
            # Filter active slots with available capacity
            available_slots = []
            for slot in slots:
                slot_info = slot.get('slotInfo', {})
                # Handle both boolean True and string 'true' for isActive
                is_active_value = slot_info.get('isActive', True)
                is_active = is_active_value is True or is_active_value == 'true' or is_active_value == True
                current_orders = int(slot_info.get('currentOrders', 0))
                max_orders = int(slot_info.get('maxOrders', 10))
                
                if is_active and current_orders < max_orders:
                    available_slots.append(slot)
            
            return available_slots
            
        except Exception as e:
            self.print_error(f"Failed to get delivery slots: {str(e)}")
            return []

    def select_delivery_slot(self):
        """Select delivery slot"""
        try:
            if not self.selected_address:
                self.print_error("Please select delivery address first")
                return None
            
            pincode = self.selected_address.get('pincode')
            if not pincode:
                self.print_error("Invalid address: missing pincode")
                return None
            
            self.print_header("SELECT DELIVERY SLOT")
            
            # Get available slots
            available_slots = self.get_available_slots(pincode)
            
            if not available_slots:
                self.print_error(f"No delivery slots available for pincode {pincode}")
                return None
            
            print(f"\n🚚 Available Delivery Slots for {pincode}:")
            print("-" * 80)
            
            for i, slot in enumerate(available_slots, 1):
                slot_info = slot.get('slotInfo', {})
                time_slot = slot_info.get('timeSlot', 'Unknown')
                slot_type = slot_info.get('slotType', 'standard')
                delivery_charge = slot_info.get('deliveryCharge', 0)
                max_orders = int(slot_info.get('maxOrders', 10))
                current_orders = int(slot_info.get('currentOrders', 0))
                available_capacity = max_orders - current_orders
                
                print(f"{i:2d}. {time_slot} ({slot_type.title()})")
                print(f"    💰 Delivery Charge: ₹{delivery_charge}")
                print(f"    📦 Available Capacity: {available_capacity} orders")
                print()
            
            try:
                index = int(input("Select slot number: ")) - 1
                if index < 0 or index >= len(available_slots):
                    self.print_error("Invalid slot number")
                    return None
            except ValueError:
                self.print_error("Invalid input")
                return None
            
            selected_slot = available_slots[index]
            self.selected_slot = selected_slot
            
            self.print_success(f"Selected delivery slot: {selected_slot.get('timeSlot')}")
            return selected_slot
            
        except Exception as e:
            self.print_error(f"Failed to select delivery slot: {str(e)}")
            return None

    def calculate_order_total(self):
        """Calculate total order amount including delivery charges"""
        try:
            if not self.cart:
                return Decimal('0')
            
            # Calculate cart total
            cart_total = Decimal('0')
            for item in self.cart:
                cart_total += Decimal(str(item['total']))
            
            # Add delivery charges
            delivery_charge = Decimal('0')
            if self.selected_slot:
                slot_info = self.selected_slot.get('slotInfo', {})
                delivery_charge = Decimal(str(slot_info.get('deliveryCharge', 0)))
            
            total_amount = cart_total + delivery_charge
            
            return {
                'cart_total': cart_total,
                'delivery_charge': delivery_charge,
                'total_amount': total_amount
            }
            
        except Exception as e:
            self.print_error(f"Failed to calculate total: {str(e)}")
            return None

    def place_order(self):
        """Place the order"""
        try:
            if not self.current_user:
                self.print_error("Please login first")
                return False
            
            if not self.cart:
                self.print_error("Cart is empty")
                return False
            
            if not self.selected_address:
                self.print_error("Please select delivery address")
                return False
            
            if not self.selected_slot:
                self.print_error("Please select delivery slot")
                return False
            
            self.print_header("ORDER CONFIRMATION")
            
            # Display order summary
            print("📋 Order Summary:")
            print("-" * 60)
            
            # Cart items
            for item in self.cart:
                print(f"• {item['name']} - {item['quantity']} {item['unit']} × ₹{item['price']} = ₹{item['total']}")
            
            # Totals
            totals = self.calculate_order_total()
            if not totals:
                return False
            
            print("-" * 60)
            print(f"Cart Total: ₹{totals['cart_total']}")
            print(f"Delivery Charge: ₹{totals['delivery_charge']}")
            print(f"Total Amount: ₹{totals['total_amount']}")
            
            # Delivery details
            print(f"\n🚚 Delivery Details:")
            print(f"Address: {self.selected_address.get('addressLine1')}, {self.selected_address.get('city')}")
            print(f"Pincode: {self.selected_address.get('pincode')}")
            slot_info = self.selected_slot.get('slotInfo', {})
            print(f"Time Slot: {slot_info.get('timeSlot')}")
            
            # Confirm order
            confirm = input(f"\nConfirm order for ₹{totals['total_amount']}? (y/N): ").strip().lower()
            if confirm != 'y':
                self.print_info("Order cancelled")
                return False
            
            # Create order
            order_id = str(uuid.uuid4())
            order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{order_id[:8].upper()}"
            order_data = {
                'orderID': order_id,
                'customerEmail': self.current_user['email'],  # Required sort key
                'orderNumber': order_number,
                'customerID': self.current_user['userID'],
                'customerInfo': {
                    'name': f"{self.current_user.get('firstName', '')} {self.current_user.get('lastName', '')}",
                    'email': self.current_user.get('email', ''),
                    'phone': self.current_user.get('phone', '')
                },
                'items': [
                    {
                        'productID': item['product_id'],
                        'variantID': item.get('variant_id'),
                        'name': item['name'],
                        'quantity': item['quantity'],
                        'unit': item['unit'],
                        'price': Decimal(str(item['price'])),
                        'total': Decimal(str(item['total']))
                    }
                    for item in self.cart
                ],
                'deliveryAddress': self.selected_address,
                'deliveryPincode': self.selected_address.get('pincode'),  # For GSI queries
                'deliveryDate': (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),  # Tomorrow
                'deliveryTimeSlot': slot_info.get('timeSlot'),  # For GSI queries
                'deliverySlot': {
                    'slotID': self.selected_slot.get('slotID'),
                    'timeSlot': slot_info.get('timeSlot'),
                    'pincode': self.selected_slot.get('pincode'),
                    'deliveryCharge': Decimal(str(slot_info.get('deliveryCharge', 0)))
                },
                'orderSummary': {
                    'cartTotal': totals['cart_total'],
                    'deliveryCharge': totals['delivery_charge'],
                    'totalAmount': totals['total_amount'],
                    'totalItems': len(self.cart)
                },
                'status': 'confirmed',
                'paymentStatus': 'pending',
                'orderDate': datetime.now(timezone.utc).isoformat(),
                'estimatedDelivery': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                'createdAt': datetime.now(timezone.utc).isoformat(),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            # Save order
            self.orders_table.put_item(Item=order_data)
            
            # Update delivery slot capacity
            try:
                self.delivery_table.update_item(
                    Key={
                        'pincodeID': self.selected_slot['pincodeID'],
                        'slotID': self.selected_slot['slotID']
                    },
                    UpdateExpression='SET slotInfo.currentOrders = slotInfo.currentOrders + :inc',
                    ExpressionAttributeValues={':inc': 1}
                )
            except Exception as e:
                # Log error but don't fail the order
                print(f"Warning: Could not update slot capacity: {e}")
            
            # Clear cart and selections
            self.cart = []
            self.selected_address = None
            self.selected_slot = None
            
            self.print_success("Order placed successfully!")
            print(f"📋 Order Number: {order_number}")
            print(f"🆔 Order ID: {order_id}")
            print(f"💰 Total Amount: ₹{totals['total_amount']}")
            print(f"📅 Estimated Delivery: Tomorrow")
            print("\n📧 Order confirmation will be sent to your email.")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to place order: {str(e)}")
            return False

    def view_order_history(self):
        """View customer order history"""
        try:
            if not self.require_authentication():
                return
            
            self.print_header("ORDER HISTORY")
            
            # Get customer orders
            response = self.orders_table.query(
                IndexName='CustomerIndex',
                KeyConditionExpression='customerEmail = :customer_email',
                ExpressionAttributeValues={':customer_email': self.current_user['email']},
                ScanIndexForward=False  # Latest orders first
            )
            
            orders = response.get('Items', [])
            
            if not orders:
                self.print_info("No orders found")
                return
            
            print(f"\n📦 Your Orders ({len(orders)} orders):")
            print("-" * 100)
            
            for order in orders:
                order_id = order.get('orderID', 'Unknown')
                order_number = order.get('orderNumber', f"ORD-{order_id[:8].upper()}")
                order_date = order.get('orderDate', '')
                status = order.get('status', 'unknown')
                total_amount = order.get('orderSummary', {}).get('totalAmount', 0)
                total_items = order.get('orderSummary', {}).get('totalItems', 0)
                
                # Format date
                try:
                    order_datetime = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    formatted_date = order_datetime.strftime('%d %b %Y, %I:%M %p')
                except:
                    formatted_date = order_date
                
                print(f"📋 Order: {order_number}")
                print(f"🆔 ID: {order_id[:8]}...")
                print(f"📅 Date: {formatted_date}")
                print(f"📊 Status: {status.title()}")
                print(f"💰 Amount: ₹{total_amount}")
                print(f"📦 Items: {total_items}")
                
                # Show delivery slot
                delivery_slot = order.get('deliverySlot', {})
                if delivery_slot:
                    print(f"🚚 Delivery: {delivery_slot.get('timeSlot', 'N/A')}")
                
                print("-" * 50)
                
        except Exception as e:
            self.print_error(f"Failed to load order history: {str(e)}")

    def startup_authentication(self):
        """Handle authentication at startup"""
        try:
            while not self.current_user:
                self.clear_screen()
                self.print_header("WELCOME TO E-COMMERCE CUSTOMER PORTAL")
                
                print("🔐 Please login or register to continue:")
                print("1. Login")
                print("2. Register New Account")
                print("0. Exit")
                print()
                print("🔑 DEFAULT TEST CREDENTIALS:")
                print("   📧 Email: john.doe@example.com")
                print("   🔒 Password: password123")
                print("   📧 Email: jane.smith@example.com")
                print("   🔒 Password: password123")
                print()
                print("⚠️  Note: Change default credentials in production!")
                print()
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self.login_menu()
                elif choice == '2':
                    self.register_customer()
                    if not self.current_user:
                        input("\nPress Enter to continue...")
                elif choice == '0':
                    self.print_info("Thank you for visiting E-commerce Store!")
                    return False
                else:
                    self.print_error("Invalid option")
                    input("\nPress Enter to continue...")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            return False
        except Exception as e:
            self.print_error(f"Authentication error: {str(e)}")
            return False

    def main_menu(self):
        """Main customer portal menu"""
        try:
            # First handle authentication
            if not self.startup_authentication():
                return
            
            while True:
                self.clear_screen()
                self.print_header("CUSTOMER PORTAL - MAIN MENU")
                
                if self.current_user:
                    print(f"👤 Welcome, {self.current_user.get('firstName', '')} {self.current_user.get('lastName', '')}!")
                    print(f"📧 {self.current_user.get('email', '')}")
                    
                    if self.cart:
                        print(f"🛒 Cart: {len(self.cart)} items")
                
                print("\n🛍️  SHOPPING:")
                print("1. Browse Categories")
                print("2. View All Products")
                print("3. Search Products")
                print("4. View Product Details")
                
                print("\n🛒 CART & ORDERS:")
                print("5. View Cart")
                print("6. Add Product to Cart")
                print("7. Manage Cart")
                print("8. Place Order")
                print("9. Order History")
                
                print("\n📍 ACCOUNT:")
                print("10. Manage Addresses")
                print("11. Profile Settings")
                
                print("\n🔐 AUTHENTICATION:")
                print("12. Logout")
                
                print("0. Exit")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    self.browse_categories()
                elif choice == '2':
                    self.browse_all_products()
                elif choice == '3':
                    self.search_products()
                elif choice == '4':
                    self.view_product_details_menu()
                elif choice == '5':
                    self.view_cart()
                    input("\nPress Enter to continue...")
                elif choice == '6':
                    self.add_product_to_cart_menu()
                elif choice == '7':
                    self.manage_cart_menu()
                elif choice == '8':
                    self.checkout_process()
                elif choice == '9':
                    self.view_order_history()
                    input("\nPress Enter to continue...")
                elif choice == '10':
                    self.manage_addresses()
                elif choice == '11':
                    self.profile_settings()
                elif choice == '12':
                    self.logout()
                    # After logout, return to authentication screen
                    if not self.startup_authentication():
                        break
                elif choice == '0':
                    self.print_info("Thank you for using E-commerce Customer Portal!")
                    break
                else:
                    self.print_error("Invalid option")
                    input("\nPress Enter to continue...")
                    
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        except Exception as e:
            self.print_error(f"Application error: {str(e)}")

    def browse_categories(self):
        """Browse products by category"""
        try:
            categories = self.list_categories()
            if not categories:
                input("\nPress Enter to continue...")
                return
            
            try:
                index = int(input("\nEnter category number (0 to go back): ")) - 1
                if index == -1:
                    return
                if index < 0 or index >= len(categories):
                    self.print_error("Invalid category number")
                    input("\nPress Enter to continue...")
                    return
            except ValueError:
                self.print_error("Invalid input")
                input("\nPress Enter to continue...")
                return
            
            selected_category = categories[index]
            products = self.list_products(category=selected_category)
            
            if products:
                print(f"\n📂 Showing products in '{selected_category.title()}' category")
                
                # Allow user to select a product from this category
                while True:
                    choice = input(f"\nSelect product (1-{len(products)}), 'a' to add to cart, or 0 to go back: ").strip().lower()
                    
                    if choice == '0':
                        break
                    elif choice == 'a':
                        # Quick add to cart
                        try:
                            prod_num = int(input(f"Enter product number to add to cart (1-{len(products)}): ")) - 1
                            if 0 <= prod_num < len(products):
                                selected_product = products[prod_num]
                                product_id = selected_product.get('productID')
                                quantity = int(input("Enter quantity (default 1): ") or "1")
                                success = self.add_to_cart(product_id, quantity)
                                if success:
                                    print(f"✅ Added {selected_product.get('name')} to cart")
                            else:
                                self.print_error("Invalid product number")
                        except ValueError:
                            self.print_error("Invalid input")
                    else:
                        try:
                            prod_index = int(choice) - 1
                            if 0 <= prod_index < len(products):
                                selected_product = products[prod_index]
                                product_id = selected_product.get('productID')
                                self.view_product_details(product_id)
                            else:
                                self.print_error("Invalid product number")
                        except ValueError:
                            self.print_error("Invalid input")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to browse categories: {str(e)}")
            input("\nPress Enter to continue...")

    def browse_all_products(self):
        """Browse all available products"""
        try:
            products = self.list_products()
            if not products:
                input("\nPress Enter to continue...")
                return
            
            # Allow user to interact with products
            while True:
                choice = input(f"\nSelect product (1-{len(products)}), 'a' to add to cart, or 0 to go back: ").strip().lower()
                
                if choice == '0':
                    break
                elif choice == 'a':
                    # Quick add to cart
                    try:
                        prod_num = int(input(f"Enter product number to add to cart (1-{len(products)}): ")) - 1
                        if 0 <= prod_num < len(products):
                            selected_product = products[prod_num]
                            product_id = selected_product.get('productID')
                            
                            # Show variants if available
                            if selected_product.get('hasVariants') and selected_product.get('variants'):
                                variants = selected_product.get('variants', [])
                                print(f"\nAvailable Variants for {selected_product.get('name')}:")
                                print("0. No variant (base product)")
                                for i, variant in enumerate(variants, 1):
                                    variant_name = variant.get('variantName', 'Unknown')
                                    variant_pricing = variant.get('pricing', {})
                                    variant_price = variant_pricing.get('sellingPrice', 0)
                                    print(f"{i}. {variant_name} - ₹{variant_price}")
                                
                                variant_choice = input(f"Select variant (0-{len(variants)}) or press Enter for base product: ").strip()
                                variant_id = None
                                if variant_choice and variant_choice != '0':
                                    try:
                                        variant_index = int(variant_choice) - 1
                                        if 0 <= variant_index < len(variants):
                                            variant_id = variants[variant_index].get('variantID')
                                    except ValueError:
                                        pass
                            else:
                                variant_id = None
                            
                            quantity = int(input("Enter quantity (default 1): ") or "1")
                            success = self.add_to_cart(product_id, quantity, variant_id)
                            if success:
                                print(f"✅ Added {selected_product.get('name')} to cart")
                        else:
                            self.print_error("Invalid product number")
                    except ValueError:
                        self.print_error("Invalid input")
                else:
                    try:
                        prod_index = int(choice) - 1
                        if 0 <= prod_index < len(products):
                            selected_product = products[prod_index]
                            product_id = selected_product.get('productID')
                            self.view_product_details(product_id)
                        else:
                            self.print_error("Invalid product number")
                    except ValueError:
                        self.print_error("Invalid input")
            
        except Exception as e:
            self.print_error(f"Failed to browse products: {str(e)}")
            input("\nPress Enter to continue...")

    def view_product_details_menu(self):
        """Menu for viewing product details"""
        try:
            # First show all products
            products = self.list_products()
            if not products:
                input("\nPress Enter to continue...")
                return
            
            try:
                choice = input(f"\nEnter product number (1-{len(products)}) or 0 to go back: ").strip()
                if choice == '0':
                    return
                
                index = int(choice) - 1
                if index < 0 or index >= len(products):
                    self.print_error("Invalid product number")
                    input("\nPress Enter to continue...")
                    return
                
                selected_product = products[index]
                product_id = selected_product.get('productID')
                product = self.view_product_details(product_id)
                input("\nPress Enter to continue...")
                
            except ValueError:
                self.print_error("Please enter a valid number")
                input("\nPress Enter to continue...")
                return
            
        except Exception as e:
            self.print_error(f"Failed to view product details: {str(e)}")
            input("\nPress Enter to continue...")

    def add_product_to_cart_menu(self):
        """Menu for adding product to cart"""
        try:
            # First show all products
            products = self.list_products()
            if not products:
                input("\nPress Enter to continue...")
                return
            
            try:
                choice = input(f"\nEnter product number (1-{len(products)}) or 0 to go back: ").strip()
                if choice == '0':
                    return
                
                index = int(choice) - 1
                if index < 0 or index >= len(products):
                    self.print_error("Invalid product number")
                    input("\nPress Enter to continue...")
                    return
                
                selected_product = products[index]
                product_id = selected_product.get('productID')
                product_name = selected_product.get('name', 'Unknown')
                
                print(f"\nSelected: {product_name}")
                
                # Show variants if available
                if selected_product.get('hasVariants') and selected_product.get('variants'):
                    variants = selected_product.get('variants', [])
                    print(f"\nAvailable Variants:")
                    print("0. No variant (base product)")
                    for i, variant in enumerate(variants, 1):
                        variant_name = variant.get('variantName', 'Unknown')
                        variant_pricing = variant.get('pricing', {})
                        variant_price = variant_pricing.get('sellingPrice', 0)
                        print(f"{i}. {variant_name} - ₹{variant_price}")
                    
                    variant_choice = input(f"\nSelect variant (0-{len(variants)}) or press Enter for no variant: ").strip()
                    variant_id = None
                    if variant_choice and variant_choice != '0':
                        try:
                            variant_index = int(variant_choice) - 1
                            if 0 <= variant_index < len(variants):
                                variant_id = variants[variant_index].get('variantID')
                                print(f"Selected variant: {variants[variant_index].get('variantName', 'Unknown')}")
                        except ValueError:
                            self.print_error("Invalid variant selection, using base product")
                else:
                    variant_id = None
                
                # Get quantity
                try:
                    quantity = int(input("Enter quantity (default 1): ") or "1")
                    if quantity <= 0:
                        self.print_error("Quantity must be positive")
                        input("\nPress Enter to continue...")
                        return
                except ValueError:
                    self.print_error("Invalid quantity")
                    input("\nPress Enter to continue...")
                    return
                
                success = self.add_to_cart(product_id, quantity, variant_id)
                input("\nPress Enter to continue...")
                
            except ValueError:
                self.print_error("Please enter a valid number")
                input("\nPress Enter to continue...")
                return
            
        except Exception as e:
            self.print_error(f"Failed to add to cart: {str(e)}")
            input("\nPress Enter to continue...")

    def manage_cart_menu(self):
        """Menu for managing cart"""
        try:
            while True:
                self.view_cart()
                
                if not self.cart:
                    input("\nPress Enter to continue...")
                    break
                
                print("\n🛒 Cart Management:")
                print("1. Update Quantity")
                print("2. Remove Item")
                print("3. Clear Cart")
                print("4. Back to Main Menu")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '1':
                    try:
                        item_num = int(input("Enter item number: "))
                        new_qty = int(input("Enter new quantity: "))
                        self.update_cart_quantity(item_num, new_qty)
                    except ValueError:
                        self.print_error("Invalid input")
                elif choice == '2':
                    try:
                        item_num = int(input("Enter item number to remove: "))
                        self.remove_from_cart(item_num)
                    except ValueError:
                        self.print_error("Invalid input")
                elif choice == '3':
                    confirm = input("Clear entire cart? (y/N): ").strip().lower()
                    if confirm == 'y':
                        self.cart = []
                        self.print_success("Cart cleared")
                elif choice == '4':
                    break
                else:
                    self.print_error("Invalid option")
                
                if choice in ['1', '2', '3']:
                    input("\nPress Enter to continue...")
                    
        except Exception as e:
            self.print_error(f"Cart management failed: {str(e)}")
            input("\nPress Enter to continue...")

    def require_authentication(self):
        """Check if user is authenticated"""
        if not self.current_user:
            self.print_error("Please login first to access this feature")
            input("\nPress Enter to continue...")
            return False
        return True

    def checkout_process(self):
        """Complete checkout process"""
        try:
            if not self.require_authentication():
                return
            
            if not self.cart:
                self.print_error("Cart is empty")
                input("\nPress Enter to continue...")
                return
            
            self.print_header("CHECKOUT PROCESS")
            
            # Step 1: Select delivery address
            print("Step 1: Select Delivery Address")
            address = self.select_delivery_address()
            if not address:
                input("\nPress Enter to continue...")
                return
            
            # Step 2: Select delivery slot
            print("\nStep 2: Select Delivery Slot")
            slot = self.select_delivery_slot()
            if not slot:
                input("\nPress Enter to continue...")
                return
            
            # Step 3: Place order
            print("\nStep 3: Place Order")
            success = self.place_order()
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Checkout failed: {str(e)}")
            input("\nPress Enter to continue...")

    def profile_settings(self):
        """Manage profile settings"""
        try:
            if not self.require_authentication():
                return
            
            self.print_header("PROFILE SETTINGS")
            
            print("👤 Current Profile:")
            print(f"Name: {self.current_user.get('firstName', '')} {self.current_user.get('lastName', '')}")
            print(f"Email: {self.current_user.get('email', '')}")
            print(f"Phone: {self.current_user.get('phone', '')}")
            
            print("\n🔧 Profile Management:")
            print("1. Update Name")
            print("2. Update Phone")
            print("3. Change Password")
            print("4. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                self.update_name()
            elif choice == '2':
                self.update_phone()
            elif choice == '3':
                self.change_password()
            elif choice == '4':
                return
            else:
                self.print_error("Invalid option")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Profile settings failed: {str(e)}")
            input("\nPress Enter to continue...")

    def update_name(self):
        """Update user name"""
        try:
            first_name = input(f"First Name ({self.current_user.get('firstName', '')}): ").strip()
            last_name = input(f"Last Name ({self.current_user.get('lastName', '')}): ").strip()
            
            if not first_name:
                first_name = self.current_user.get('firstName', '')
            if not last_name:
                last_name = self.current_user.get('lastName', '')
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET firstName = :first, lastName = :last, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':first': first_name,
                    ':last': last_name,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['firstName'] = first_name
            self.current_user['lastName'] = last_name
            
            self.print_success("Name updated successfully!")
            
        except Exception as e:
            self.print_error(f"Failed to update name: {str(e)}")

    def update_phone(self):
        """Update phone number"""
        try:
            phone = input(f"Phone ({self.current_user.get('phone', '')}): ").strip()
            
            if not phone:
                phone = self.current_user.get('phone', '')
            
            # Update user record
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET phone = :phone, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':phone': phone,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['phone'] = phone
            
            self.print_success("Phone updated successfully!")
            
        except Exception as e:
            self.print_error(f"Failed to update phone: {str(e)}")

    def change_password(self):
        """Change user password"""
        try:
            current_password = getpass.getpass("Current Password: ")
            new_password = getpass.getpass("New Password: ")
            confirm_password = getpass.getpass("Confirm New Password: ")
            
            if not all([current_password, new_password, confirm_password]):
                self.print_error("All fields are required")
                return
            
            # Verify current password
            if self.hash_password(current_password) != self.current_user.get('passwordHash'):
                self.print_error("Current password is incorrect")
                return
            
            if new_password != confirm_password:
                self.print_error("New passwords do not match")
                return
            
            # Update password
            new_password_hash = self.hash_password(new_password)
            
            self.users_table.update_item(
                Key={
                    'userID': self.current_user['userID'],
                    'email': self.current_user['email']
                },
                UpdateExpression='SET passwordHash = :password, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':password': new_password_hash,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update current user data
            self.current_user['passwordHash'] = new_password_hash
            
            self.print_success("Password changed successfully!")
            
        except Exception as e:
            self.print_error(f"Failed to change password: {str(e)}")

    def login_menu(self):
        """Login menu"""
        try:
            self.print_header("CUSTOMER LOGIN")
            
            email = input("Email: ").strip()
            password = getpass.getpass("Password: ")
            
            if not email or not password:
                self.print_error("Email and password are required")
                input("\nPress Enter to continue...")
                return
            
            success = self.authenticate_user(email, password)
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Login failed: {str(e)}")
            input("\nPress Enter to continue...")

    def logout(self):
        """Logout user"""
        try:
            self.current_user = None
            self.cart = []
            self.selected_address = None
            self.selected_slot = None
            self.print_success("Logged out successfully!")
            input("\nPress Enter to continue...")
        except Exception as e:
            self.print_error(f"Logout failed: {str(e)}")
            input("\nPress Enter to continue...")

    def run(self):
        """Main application entry point"""
        try:
            self.main_menu()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        except Exception as e:
            self.print_error(f"Application error: {str(e)}")


def main():
    """Main function to run the customer portal"""
    try:
        portal = CustomerPortal()
        portal.run()
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user.")
    except Exception as e:
        print(f"\n❌ Application error: {str(e)}")
        print("Please check your AWS credentials and DynamoDB table setup.")


if __name__ == "__main__":
    main()
