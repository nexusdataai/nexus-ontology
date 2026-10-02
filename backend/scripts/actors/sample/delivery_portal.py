#!/usr/bin/env python3
# delivery_portal.py
"""
E-commerce - Delivery Portal
Complete delivery personnel functionality: Route management, order delivery, 
payment collection, delivery confirmation, and GPS tracking
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
from boto3.dynamodb.conditions import Key


class DeliveryPortal:
    """E-commerce Delivery Portal - Complete Delivery Experience"""
    
    def __init__(self):
        self.region_name = 'ap-south-1'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
        
        # Aurora Spark Theme Optimized Tables
        self.users_table = self.dynamodb.Table('AuroraSparkTheme-Users')
        self.staff_table = self.dynamodb.Table('AuroraSparkTheme-Staff')
        self.orders_table = self.dynamodb.Table('AuroraSparkTheme-Orders')
        self.delivery_table = self.dynamodb.Table('AuroraSparkTheme-Delivery')
        self.logistics_table = self.dynamodb.Table('AuroraSparkTheme-Logistics')
        self.system_table = self.dynamodb.Table('AuroraSparkTheme-System')
        self.analytics_table = self.dynamodb.Table('AuroraSparkTheme-Analytics')
        
        self.current_user = None
        self.current_route = None
        self.vehicle_info = None
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 100)
        print(f"🚚 [E-COMMERCE - DELIVERY PORTAL] {title}")
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

    def authenticate_delivery_personnel(self) -> bool:
        """Authenticate delivery personnel"""
        try:
            self.clear_screen()
            self.print_header("DELIVERY PERSONNEL AUTHENTICATION")
            
            print("🚚 Welcome to E-commerce Delivery Portal")
            print("Please login with your delivery personnel credentials")
            print("-" * 60)
            print()
            print("🔑 DEFAULT TEST CREDENTIALS:")
            print("   🆔 Employee ID: EMP-001")
            print("   🔒 Password: password123")
            print("   (Note: Using existing staff member for testing)")
            print()
            print("⚠️  Note: Change default credentials in production!")
            print("-" * 60)
            print()
            
            employee_id = input("Employee ID: ").strip()
            if not employee_id:
                self.print_error("Employee ID is required")
                return False
            
            password = getpass.getpass("Password: ")
            if not password:
                self.print_error("Password is required")
                return False
            
            # Hash the password for comparison
            password_hash = self.hash_password(password)
            
            # Check staff table for delivery personnel using GSI
            response = self.staff_table.query(
                IndexName='EmployeeIndex',
                KeyConditionExpression=Key('employeeID').eq(employee_id)
            )
            
            items = response.get('Items', [])
            if not items:
                self.print_error("Invalid employee ID or password")
                return False
            
            staff_member = items[0]  # Get the first matching staff member
            
            # For demo purposes, accept password123 for EMP-001
            if employee_id == 'EMP-001' and password == 'password123':
                # Demo authentication successful
                pass
            else:
                # Verify password hash if available
                if staff_member.get('passwordHash') != password_hash:
                    self.print_error("Invalid employee ID or password")
                    return False
                
                # Check if user has delivery role
                roles = staff_member.get('roles', [])
                if 'delivery_personnel' not in roles:
                    self.print_error("Access denied. You don't have delivery personnel privileges")
                    return False
            
            # Check if user is active
            if staff_member.get('status', '') != 'active':
                self.print_error("Your account is not active. Please contact administration")
                return False
            
            # Set current user
            self.current_user = staff_member
            
            # Get vehicle information if assigned
            vehicle_assigned = staff_member.get('vehicleAssigned')
            if vehicle_assigned:
                self.vehicle_info = {
                    'vehicleNumber': vehicle_assigned,
                    'type': staff_member.get('vehicleType', 'bike'),
                    'capacity': staff_member.get('vehicleCapacity', '50kg')
                }
            
            self.print_success(f"Welcome, {staff_member.get('name', 'Delivery Personnel')}!")
            
            # Display user info
            print(f"\n👤 PERSONNEL INFO:")
            print(f"   Name: {staff_member.get('name', 'N/A')}")
            print(f"   Employee ID: {employee_id}")
            print(f"   Department: {staff_member.get('department', 'Delivery')}")
            print(f"   Shift: {staff_member.get('currentShift', 'N/A')}")
            
            if self.vehicle_info:
                print(f"\n🚛 ASSIGNED VEHICLE:")
                print(f"   Vehicle: {self.vehicle_info['vehicleNumber']}")
                print(f"   Type: {self.vehicle_info['type'].title()}")
                print(f"   Capacity: {self.vehicle_info['capacity']}")
            
            input("\nPress Enter to continue...")
            return True
            
        except Exception as e:
            self.print_error(f"Authentication failed: {str(e)}")
            return False

    def logout(self):
        """Logout current user"""
        if self.current_user:
            name = self.current_user.get('name', 'User')
            self.current_user = None
            self.current_route = None
            self.vehicle_info = None
            self.print_success(f"Goodbye, {name}!")
        else:
            self.print_info("No user logged in")

    def view_assigned_routes(self):
        """View routes assigned to the current delivery personnel"""
        try:
            self.clear_screen()
            self.print_header("MY ASSIGNED ROUTES")
            
            if not self.current_user:
                self.print_error("Please login first")
                return
            
            employee_id = self.current_user.get('employeeID')
            today = datetime.now(timezone.utc).date().isoformat()
            
            # Get routes assigned to this delivery personnel
            response = self.logistics_table.scan(
                FilterExpression='#driver_id = :driver_id AND #route_date = :today',
                ExpressionAttributeNames={
                    '#driver_id': 'driverID',
                    '#route_date': 'routeDate'
                },
                ExpressionAttributeValues={
                    ':driver_id': employee_id,
                    ':today': today
                }
            )
            
            routes = response.get('Items', [])
            
            if not routes:
                self.print_info("No routes assigned for today")
                input("Press Enter to continue...")
                return
            
            print(f"📋 ROUTES FOR TODAY ({len(routes)} routes):")
            print("=" * 80)
            
            for i, route in enumerate(routes, 1):
                route_code = route.get('routeCode', 'N/A')
                route_name = route.get('routeName', 'Unnamed Route')
                status = route.get('status', 'unknown')
                vehicle_number = route.get('vehicleNumber', 'N/A')
                total_orders = route.get('totalOrders', 0)
                completed_orders = route.get('completedOrders', 0)
                estimated_duration = route.get('estimatedDuration', 0)
                
                # Status emoji
                status_emoji = {
                    'planned': '📅',
                    'in_progress': '🚛',
                    'completed': '✅',
                    'cancelled': '❌'
                }.get(status, '❓')
                
                print(f"\n{i}. {status_emoji} {route_name} ({route_code})")
                print(f"   Status: {status.title()}")
                print(f"   Vehicle: {vehicle_number}")
                print(f"   Orders: {completed_orders}/{total_orders}")
                print(f"   Est. Duration: {estimated_duration} minutes")
                
                if status == 'planned':
                    print(f"   ⚡ Ready to start!")
                elif status == 'in_progress':
                    progress = (completed_orders / total_orders * 100) if total_orders > 0 else 0
                    print(f"   📊 Progress: {progress:.1f}%")
            
            print(f"\n📊 SUMMARY:")
            planned_routes = len([r for r in routes if r.get('status') == 'planned'])
            in_progress_routes = len([r for r in routes if r.get('status') == 'in_progress'])
            completed_routes = len([r for r in routes if r.get('status') == 'completed'])
            
            print(f"   📅 Planned: {planned_routes}")
            print(f"   🚛 In Progress: {in_progress_routes}")
            print(f"   ✅ Completed: {completed_routes}")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to load routes: {str(e)}")
            input("Press Enter to continue...")

    def start_route(self):
        """Start a planned delivery route"""
        try:
            self.clear_screen()
            self.print_header("START DELIVERY ROUTE")
            
            if not self.current_user:
                self.print_error("Please login first")
                return
            
            employee_id = self.current_user.get('employeeID')
            today = datetime.now(timezone.utc).date().isoformat()
            
            # Get planned routes
            response = self.logistics_table.scan(
                FilterExpression='#driver_id = :driver_id AND #route_date = :today AND #status = :status',
                ExpressionAttributeNames={
                    '#driver_id': 'driverID',
                    '#route_date': 'routeDate',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':driver_id': employee_id,
                    ':today': today,
                    ':status': 'planned'
                }
            )
            
            planned_routes = response.get('Items', [])
            
            if not planned_routes:
                self.print_info("No planned routes available to start")
                input("Press Enter to continue...")
                return
            
            print("📋 SELECT ROUTE TO START:")
            print("=" * 50)
            
            for i, route in enumerate(planned_routes, 1):
                route_code = route.get('routeCode', 'N/A')
                route_name = route.get('routeName', 'Unnamed Route')
                total_orders = route.get('totalOrders', 0)
                vehicle_number = route.get('vehicleNumber', 'N/A')
                
                print(f"{i}. {route_name} ({route_code})")
                print(f"   Vehicle: {vehicle_number}")
                print(f"   Orders: {total_orders}")
            
            print("0. Cancel")
            
            try:
                choice = int(input("\nSelect route: ").strip())
                if choice == 0:
                    return
                
                if 1 <= choice <= len(planned_routes):
                    selected_route = planned_routes[choice - 1]
                    route_id = selected_route.get('routeID')
                    
                    # Update route status to in_progress
                    self.logistics_table.update_item(
                        Key={'routeID': route_id},
                        UpdateExpression='SET #status = :status, #start_time = :start_time',
                        ExpressionAttributeNames={
                            '#status': 'status',
                            '#start_time': 'actualStartTime'
                        },
                        ExpressionAttributeValues={
                            ':status': 'in_progress',
                            ':start_time': datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                    # Set current route
                    self.current_route = selected_route
                    self.current_route['status'] = 'in_progress'
                    
                    self.print_success(f"Route started: {selected_route.get('routeName', 'Route')}")
                    self.print_info("GPS tracking initiated (simulated)")
                    
                    input("Press Enter to continue...")
                    
                else:
                    self.print_error("Invalid selection")
                    
            except ValueError:
                self.print_error("Please enter a valid number")
                
        except Exception as e:
            self.print_error(f"Failed to start route: {str(e)}")
            input("Press Enter to continue...")

    def view_route_orders(self):
        """View orders in current route"""
        try:
            self.clear_screen()
            self.print_header("ROUTE ORDERS")
            
            if not self.current_route:
                self.print_error("No active route. Please start a route first")
                input("Press Enter to continue...")
                return
            
            route_id = self.current_route.get('routeID')
            
            # Get orders for this route
            response = self.orders_table.scan(
                FilterExpression='#route_id = :route_id',
                ExpressionAttributeNames={'#route_id': 'routeID'},
                ExpressionAttributeValues={':route_id': route_id}
            )
            
            orders = response.get('Items', [])
            
            if not orders:
                self.print_info("No orders found for this route")
                input("Press Enter to continue...")
                return
            
            route_name = self.current_route.get('routeName', 'Current Route')
            print(f"📦 ORDERS IN {route_name.upper()}:")
            print("=" * 80)
            
            # Sort orders by delivery sequence or address
            orders.sort(key=lambda x: x.get('deliverySequence', 999))
            
            for i, order in enumerate(orders, 1):
                order_id = order.get('orderID', 'N/A')
                customer_name = order.get('customerName', 'Unknown Customer')
                status = order.get('status', 'unknown')
                total_amount = order.get('totalAmount', 0)
                payment_method = order.get('paymentMethod', 'unknown')
                address = order.get('deliveryAddress', {})
                
                # Status emoji
                status_emoji = {
                    'packed': '📦',
                    'out_for_delivery': '🚛',
                    'delivered': '✅',
                    'failed_delivery': '❌',
                    'returned': '↩️'
                }.get(status, '❓')
                
                print(f"\n{i}. {status_emoji} Order #{order_id}")
                print(f"   Customer: {customer_name}")
                print(f"   Status: {status.replace('_', ' ').title()}")
                print(f"   Amount: ₹{float(total_amount):.2f}")
                print(f"   Payment: {payment_method.upper()}")
                
                # Address details
                if address:
                    street = address.get('street', '')
                    area = address.get('area', '')
                    pincode = address.get('pincode', '')
                    print(f"   Address: {street}, {area} - {pincode}")
                
                # Phone number for contact
                phone = order.get('customerPhone', '')
                if phone:
                    print(f"   Phone: {phone}")
            
            print(f"\n📊 ROUTE SUMMARY:")
            pending_orders = len([o for o in orders if o.get('status') not in ['delivered', 'returned']])
            delivered_orders = len([o for o in orders if o.get('status') == 'delivered'])
            total_value = sum(float(o.get('totalAmount', 0)) for o in orders)
            
            print(f"   📦 Total Orders: {len(orders)}")
            print(f"   ⏳ Pending: {pending_orders}")
            print(f"   ✅ Delivered: {delivered_orders}")
            print(f"   💰 Total Value: ₹{total_value:.2f}")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to load route orders: {str(e)}")
            input("Press Enter to continue...")

    def deliver_order(self):
        """Process order delivery with confirmation"""
        try:
            self.clear_screen()
            self.print_header("ORDER DELIVERY")
            
            if not self.current_route:
                self.print_error("No active route. Please start a route first")
                input("Press Enter to continue...")
                return
            
            route_id = self.current_route.get('routeID')
            
            # Get pending orders for this route
            response = self.orders_table.scan(
                FilterExpression='#route_id = :route_id AND #status IN (:status1, :status2)',
                ExpressionAttributeNames={
                    '#route_id': 'routeID',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':route_id': route_id,
                    ':status1': 'packed',
                    ':status2': 'out_for_delivery'
                }
            )
            
            pending_orders = response.get('Items', [])
            
            if not pending_orders:
                self.print_info("No pending orders for delivery")
                input("Press Enter to continue...")
                return
            
            print("📦 SELECT ORDER TO DELIVER:")
            print("=" * 60)
            
            for i, order in enumerate(pending_orders, 1):
                order_id = order.get('orderID', 'N/A')
                customer_name = order.get('customerName', 'Unknown Customer')
                total_amount = order.get('totalAmount', 0)
                payment_method = order.get('paymentMethod', 'unknown')
                address = order.get('deliveryAddress', {})
                
                print(f"{i}. Order #{order_id}")
                print(f"   Customer: {customer_name}")
                print(f"   Amount: ₹{float(total_amount):.2f}")
                print(f"   Payment: {payment_method.upper()}")
                
                if address:
                    street = address.get('street', '')
                    area = address.get('area', '')
                    pincode = address.get('pincode', '')
                    print(f"   Address: {street}, {area} - {pincode}")
                print()
            
            print("0. Cancel")
            
            try:
                choice = int(input("Select order: ").strip())
                if choice == 0:
                    return
                
                if 1 <= choice <= len(pending_orders):
                    selected_order = pending_orders[choice - 1]
                    self._process_delivery(selected_order)
                else:
                    self.print_error("Invalid selection")
                    
            except ValueError:
                self.print_error("Please enter a valid number")
                
        except Exception as e:
            self.print_error(f"Failed to process delivery: {str(e)}")
            input("Press Enter to continue...")

    def _process_delivery(self, order: Dict[str, Any]):
        """Process individual order delivery"""
        try:
            order_id = order.get('orderID')
            customer_name = order.get('customerName', 'Customer')
            total_amount = float(order.get('totalAmount', 0))
            payment_method = order.get('paymentMethod', 'unknown')
            
            self.clear_screen()
            self.print_header(f"DELIVERING ORDER #{order_id}")
            
            print(f"👤 Customer: {customer_name}")
            print(f"💰 Amount: ₹{total_amount:.2f}")
            print(f"💳 Payment: {payment_method.upper()}")
            
            # Delivery options
            print("\n🚚 DELIVERY OPTIONS:")
            print("1. ✅ Successful Delivery")
            print("2. ❌ Failed Delivery")
            print("3. ↩️ Return to Warehouse")
            print("0. Cancel")
            
            choice = input("\nSelect delivery status: ").strip()
            
            if choice == '0':
                return
            elif choice == '1':
                self._successful_delivery(order)
            elif choice == '2':
                self._failed_delivery(order)
            elif choice == '3':
                self._return_order(order)
            else:
                self.print_error("Invalid option")
                
        except Exception as e:
            self.print_error(f"Delivery processing failed: {str(e)}")

    def _successful_delivery(self, order: Dict[str, Any]):
        """Process successful delivery"""
        try:
            order_id = order.get('orderID')
            payment_method = order.get('paymentMethod', 'unknown')
            total_amount = float(order.get('totalAmount', 0))
            
            print("\n✅ DELIVERY CONFIRMATION:")
            
            # Customer verification
            print("📋 CUSTOMER VERIFICATION:")
            customer_verified = input("Customer verified? (y/n): ").strip().lower() == 'y'
            
            if not customer_verified:
                self.print_error("Cannot complete delivery without customer verification")
                input("Press Enter to continue...")
                return
            
            # Collect payment if COD
            payment_collected = True
            if payment_method.lower() == 'cod':
                print(f"\n💰 COD PAYMENT COLLECTION:")
                print(f"Amount to collect: ₹{total_amount:.2f}")
                payment_collected = input("Payment collected? (y/n): ").strip().lower() == 'y'
                
                if not payment_collected:
                    self.print_error("Cannot complete COD delivery without payment collection")
                    input("Press Enter to continue...")
                    return
            
            # Delivery proof
            print("\n📸 DELIVERY PROOF:")
            signature_obtained = input("Customer signature obtained? (y/n): ").strip().lower() == 'y'
            photo_taken = input("Delivery photo taken? (y/n): ").strip().lower() == 'y'
            
            # Customer feedback (optional)
            print("\n💬 CUSTOMER FEEDBACK (Optional):")
            feedback = input("Any feedback from customer: ").strip()
            
            # Update order status
            delivery_timestamp = datetime.now(timezone.utc).isoformat()
            
            update_expression = 'SET #status = :status, #delivery_time = :delivery_time, #delivered_by = :delivered_by'
            expression_values = {
                ':status': 'delivered',
                ':delivery_time': delivery_timestamp,
                ':delivered_by': self.current_user.get('employeeID')
            }
            expression_names = {
                '#status': 'status',
                '#delivery_time': 'deliveryTime',
                '#delivered_by': 'deliveredBy'
            }
            
            # Add delivery proof details
            if signature_obtained or photo_taken:
                delivery_proof = {
                    'signature': signature_obtained,
                    'photo': photo_taken,
                    'timestamp': delivery_timestamp
                }
                update_expression += ', #delivery_proof = :delivery_proof'
                expression_names['#delivery_proof'] = 'deliveryProof'
                expression_values[':delivery_proof'] = delivery_proof
            
            # Add feedback if provided
            if feedback:
                update_expression += ', #customer_feedback = :feedback'
                expression_names['#customer_feedback'] = 'customerFeedback'
                expression_values[':feedback'] = feedback
            
            # Record COD payment if applicable
            if payment_method.lower() == 'cod' and payment_collected:
                payment_record = {
                    'paymentID': str(uuid.uuid4()),
                    'orderID': order_id,
                    'amount': total_amount,
                    'method': 'cod',
                    'status': 'completed',
                    'collectedBy': self.current_user.get('employeeID'),
                    'collectionTime': delivery_timestamp
                }
                
                update_expression += ', #payment_record = :payment_record'
                expression_names['#payment_record'] = 'paymentRecord'
                expression_values[':payment_record'] = payment_record
            
            # Update the order
            self.orders_table.update_item(
                Key={'orderID': order_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
            self.print_success(f"Order #{order_id} delivered successfully!")
            
            if payment_method.lower() == 'cod':
                self.print_success(f"COD payment of ₹{total_amount:.2f} collected")
            
            # Update route progress
            self._update_route_progress()
            
            input("Press Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to process successful delivery: {str(e)}")
            input("Press Enter to continue...")

    def _failed_delivery(self, order: Dict[str, Any]):
        """Process failed delivery"""
        try:
            order_id = order.get('orderID')
            
            print("\n❌ FAILED DELIVERY:")
            print("Select reason for failed delivery:")
            print("1. Customer not available")
            print("2. Wrong address")
            print("3. Customer refused delivery")
            print("4. Payment issue (COD)")
            print("5. Other")
            
            reason_choice = input("Select reason: ").strip()
            reason_map = {
                '1': 'customer_not_available',
                '2': 'wrong_address',
                '3': 'customer_refused',
                '4': 'payment_issue',
                '5': 'other'
            }
            
            failure_reason = reason_map.get(reason_choice, 'other')
            
            # Additional notes
            notes = input("Additional notes (optional): ").strip()
            
            # Reschedule option
            print("\nReschedule delivery?")
            print("1. Reschedule for today")
            print("2. Reschedule for tomorrow")
            print("3. Return to warehouse")
            
            reschedule_choice = input("Select option: ").strip()
            
            new_status = 'failed_delivery'
            if reschedule_choice == '1':
                new_status = 'rescheduled_today'
            elif reschedule_choice == '2':
                new_status = 'rescheduled_tomorrow'
            elif reschedule_choice == '3':
                new_status = 'returned'
            
            # Update order
            failure_record = {
                'reason': failure_reason,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'attemptedBy': self.current_user.get('employeeID'),
                'notes': notes
            }
            
            self.orders_table.update_item(
                Key={'orderID': order_id},
                UpdateExpression='SET #status = :status, #failure_record = :failure_record',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#failure_record': 'failureRecord'
                },
                ExpressionAttributeValues={
                    ':status': new_status,
                    ':failure_record': failure_record
                }
            )
            
            self.print_success(f"Order #{order_id} marked as failed delivery")
            
            if new_status.startswith('rescheduled'):
                self.print_info("Order scheduled for redelivery")
            elif new_status == 'returned':
                self.print_info("Order will be returned to warehouse")
            
            input("Press Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to process failed delivery: {str(e)}")
            input("Press Enter to continue...")

    def _return_order(self, order: Dict[str, Any]):
        """Process order return to warehouse"""
        try:
            order_id = order.get('orderID')
            
            print("\n↩️ RETURN TO WAREHOUSE:")
            return_reason = input("Reason for return: ").strip()
            
            if not return_reason:
                self.print_error("Return reason is required")
                return
            
            # Update order status
            return_record = {
                'reason': return_reason,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'returnedBy': self.current_user.get('employeeID')
            }
            
            self.orders_table.update_item(
                Key={'orderID': order_id},
                UpdateExpression='SET #status = :status, #return_record = :return_record',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#return_record': 'returnRecord'
                },
                ExpressionAttributeValues={
                    ':status': 'returned',
                    ':return_record': return_record
                }
            )
            
            self.print_success(f"Order #{order_id} marked for return to warehouse")
            input("Press Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to process return: {str(e)}")
            input("Press Enter to continue...")

    def _update_route_progress(self):
        """Update route progress after delivery"""
        try:
            if not self.current_route:
                return
            
            route_id = self.current_route.get('routeID')
            
            # Get current route orders to calculate progress
            response = self.orders_table.scan(
                FilterExpression='#route_id = :route_id',
                ExpressionAttributeNames={'#route_id': 'routeID'},
                ExpressionAttributeValues={':route_id': route_id}
            )
            
            orders = response.get('Items', [])
            total_orders = len(orders)
            completed_orders = len([o for o in orders if o.get('status') in ['delivered', 'returned']])
            
            # Update route progress
            self.logistics_table.update_item(
                Key={'routeID': route_id},
                UpdateExpression='SET #completed = :completed, #total = :total',
                ExpressionAttributeNames={
                    '#completed': 'completedOrders',
                    '#total': 'totalOrders'
                },
                ExpressionAttributeValues={
                    ':completed': completed_orders,
                    ':total': total_orders
                }
            )
            
            # Check if route is complete
            if completed_orders >= total_orders:
                self.logistics_table.update_item(
                    Key={'routeID': route_id},
                    UpdateExpression='SET #status = :status, #end_time = :end_time',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#end_time': 'actualEndTime'
                    },
                    ExpressionAttributeValues={
                        ':status': 'completed',
                        ':end_time': datetime.now(timezone.utc).isoformat()
                    }
                )
                
                self.print_success("🎉 Route completed! All orders delivered/returned")
                self.current_route = None
                
        except Exception as e:
            self.print_error(f"Failed to update route progress: {str(e)}")

    def view_navigation_help(self):
        """Display navigation assistance and GPS tracking"""
        try:
            self.clear_screen()
            self.print_header("NAVIGATION & GPS TRACKING")
            
            if not self.current_route:
                self.print_error("No active route. Please start a route first")
                input("Press Enter to continue...")
                return
            
            route_name = self.current_route.get('routeName', 'Current Route')
            
            print(f"🗺️ NAVIGATION FOR: {route_name}")
            print("=" * 60)
            
            # Simulated GPS status
            print("📍 GPS STATUS:")
            print("   Status: ✅ Active")
            print("   Signal: Strong (4/4 bars)")
            print("   Accuracy: ±3 meters")
            print("   Last Update: Just now")
            
            # Current location (simulated)
            print("\n📌 CURRENT LOCATION:")
            print("   Latitude: 17.4065° N")
            print("   Longitude: 78.4772° E")
            print("   Address: Hyderabad, Telangana")
            print("   Speed: 25 km/h")
            
            # Route information
            route_id = self.current_route.get('routeID')
            
            # Get next delivery location
            response = self.orders_table.scan(
                FilterExpression='#route_id = :route_id AND #status IN (:status1, :status2)',
                ExpressionAttributeNames={
                    '#route_id': 'routeID',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':route_id': route_id,
                    ':status1': 'packed',
                    ':status2': 'out_for_delivery'
                }
            )
            
            pending_orders = response.get('Items', [])
            
            if pending_orders:
                # Sort by delivery sequence
                pending_orders.sort(key=lambda x: x.get('deliverySequence', 999))
                next_order = pending_orders[0]
                
                print("\n🎯 NEXT DELIVERY:")
                print(f"   Order: #{next_order.get('orderID', 'N/A')}")
                print(f"   Customer: {next_order.get('customerName', 'Unknown')}")
                
                address = next_order.get('deliveryAddress', {})
                if address:
                    street = address.get('street', '')
                    area = address.get('area', '')
                    pincode = address.get('pincode', '')
                    print(f"   Address: {street}, {area} - {pincode}")
                
                # Simulated navigation info
                print(f"   Distance: {random.randint(2, 15)} km")
                print(f"   ETA: {random.randint(10, 45)} minutes")
                print(f"   Route: Via {random.choice(['Main Road', 'Highway', 'Inner Road'])}")
                
                phone = next_order.get('customerPhone', '')
                if phone:
                    print(f"   Phone: {phone}")
            else:
                print("\n✅ ALL DELIVERIES COMPLETED!")
            
            print("\n🛠️ NAVIGATION OPTIONS:")
            print("1. 📱 Open in Google Maps (simulated)")
            print("2. 📞 Call Customer")
            print("3. 🚨 Report Issue")
            print("4. 📍 Update Current Location")
            print("5. 🔄 Refresh GPS")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '1':
                self.print_info("Opening navigation in Google Maps... (simulated)")
                self.print_success("GPS navigation started!")
            elif choice == '2':
                if pending_orders:
                    phone = pending_orders[0].get('customerPhone', 'N/A')
                    self.print_info(f"Calling customer at {phone}... (simulated)")
                else:
                    self.print_error("No pending deliveries to call")
            elif choice == '3':
                self._report_navigation_issue()
            elif choice == '4':
                self.print_info("Updating GPS location... (simulated)")
                self.print_success("Location updated successfully!")
            elif choice == '5':
                self.print_info("Refreshing GPS signal... (simulated)")
                self.print_success("GPS refreshed successfully!")
            elif choice == '0':
                return
            else:
                self.print_error("Invalid option")
            
            if choice != '0':
                input("Press Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Navigation error: {str(e)}")
            input("Press Enter to continue...")

    def _report_navigation_issue(self):
        """Report navigation or route issues"""
        try:
            print("\n🚨 REPORT NAVIGATION ISSUE:")
            print("1. GPS signal lost")
            print("2. Road blocked/construction")
            print("3. Vehicle breakdown")
            print("4. Traffic jam")
            print("5. Other")
            
            issue_choice = input("Select issue type: ").strip()
            issue_map = {
                '1': 'gps_signal_lost',
                '2': 'road_blocked',
                '3': 'vehicle_breakdown',
                '4': 'traffic_jam',
                '5': 'other'
            }
            
            issue_type = issue_map.get(issue_choice, 'other')
            description = input("Describe the issue: ").strip()
            
            if not description:
                self.print_error("Issue description is required")
                return
            
            # Create issue report
            issue_report = {
                'issueID': str(uuid.uuid4()),
                'routeID': self.current_route.get('routeID'),
                'reportedBy': self.current_user.get('employeeID'),
                'issueType': issue_type,
                'description': description,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'reported',
                'location': {
                    'latitude': '17.4065',
                    'longitude': '78.4772',
                    'address': 'Current Location'
                }
            }
            
            # In a real system, this would be stored in an issues table
            self.print_success("Issue reported successfully!")
            self.print_info("Logistics team has been notified")
            
        except Exception as e:
            self.print_error(f"Failed to report issue: {str(e)}")

    def view_delivery_performance(self):
        """View delivery performance metrics"""
        try:
            self.clear_screen()
            self.print_header("DELIVERY PERFORMANCE")
            
            if not self.current_user:
                self.print_error("Please login first")
                return
            
            employee_id = self.current_user.get('employeeID')
            employee_name = self.current_user.get('name', 'Delivery Personnel')
            
            print(f"📊 PERFORMANCE METRICS FOR: {employee_name}")
            print("=" * 60)
            
            # Today's performance (simulated data)
            today_deliveries = random.randint(8, 25)
            today_successful = random.randint(int(today_deliveries * 0.8), today_deliveries)
            today_failed = today_deliveries - today_successful
            today_cod_collected = random.randint(5000, 25000)
            
            print("📅 TODAY'S PERFORMANCE:")
            print(f"   Total Deliveries: {today_deliveries}")
            print(f"   ✅ Successful: {today_successful}")
            print(f"   ❌ Failed: {today_failed}")
            print(f"   📈 Success Rate: {(today_successful/today_deliveries*100):.1f}%")
            print(f"   💰 COD Collected: ₹{today_cod_collected:,}")
            
            # Weekly performance
            week_deliveries = random.randint(50, 150)
            week_successful = random.randint(int(week_deliveries * 0.85), week_deliveries)
            week_cod_collected = random.randint(25000, 100000)
            
            print(f"\n📈 THIS WEEK:")
            print(f"   Total Deliveries: {week_deliveries}")
            print(f"   ✅ Successful: {week_successful}")
            print(f"   📈 Success Rate: {(week_successful/week_deliveries*100):.1f}%")
            print(f"   💰 COD Collected: ₹{week_cod_collected:,}")
            
            # Monthly performance
            month_deliveries = random.randint(200, 600)
            month_successful = random.randint(int(month_deliveries * 0.87), month_deliveries)
            month_cod_collected = random.randint(100000, 400000)
            
            print(f"\n📊 THIS MONTH:")
            print(f"   Total Deliveries: {month_deliveries}")
            print(f"   ✅ Successful: {month_successful}")
            print(f"   📈 Success Rate: {(month_successful/month_deliveries*100):.1f}%")
            print(f"   💰 COD Collected: ₹{month_cod_collected:,}")
            
            # Performance badges/achievements
            print(f"\n🏆 ACHIEVEMENTS:")
            achievements = []
            
            if today_successful >= 20:
                achievements.append("🌟 High Performer (20+ deliveries today)")
            
            if (today_successful/today_deliveries) >= 0.95:
                achievements.append("🎯 Perfect Delivery Rate (95%+ success)")
            
            if today_cod_collected >= 20000:
                achievements.append("💰 Top COD Collector (₹20k+ today)")
            
            if not achievements:
                achievements.append("💪 Keep up the good work!")
            
            for achievement in achievements:
                print(f"   {achievement}")
            
            # Recent delivery feedback
            print(f"\n💬 RECENT CUSTOMER FEEDBACK:")
            feedbacks = [
                "Excellent service, very polite delivery person! ⭐⭐⭐⭐⭐",
                "On time delivery, thank you! ⭐⭐⭐⭐⭐",
                "Professional and courteous ⭐⭐⭐⭐",
                "Quick delivery, good service ⭐⭐⭐⭐⭐"
            ]
            
            for feedback in random.sample(feedbacks, min(2, len(feedbacks))):
                print(f"   • {feedback}")
            
            input("\nPress Enter to continue...")
            
        except Exception as e:
            self.print_error(f"Failed to load performance metrics: {str(e)}")
            input("Press Enter to continue...")

    def main_menu(self):
        """Main menu for delivery portal"""
        while True:
            try:
                self.clear_screen()
                self.print_header("MAIN MENU")
                
                if self.current_user:
                    name = self.current_user.get('name', 'Delivery Personnel')
                    employee_id = self.current_user.get('employeeID', 'N/A')
                    print(f"👤 Logged in as: {name} (ID: {employee_id})")
                    
                    if self.vehicle_info:
                        print(f"🚛 Vehicle: {self.vehicle_info['vehicleNumber']} ({self.vehicle_info['type'].title()})")
                    
                    if self.current_route:
                        route_name = self.current_route.get('routeName', 'Active Route')
                        print(f"🗺️ Active Route: {route_name}")
                    
                    print("-" * 80)
                
                print("🚚 E-COMMERCE DELIVERY PORTAL")
                print("=" * 50)
                
                if not self.current_user:
                    print("1. 🔐 Login")
                    print("0. ❌ Exit")
                else:
                    print("📋 ROUTE MANAGEMENT:")
                    print("1. 🗺️ View My Routes")
                    print("2. ▶️ Start Route")
                    print("3. 📦 View Route Orders")
                    
                    print("\n🚚 DELIVERY OPERATIONS:")
                    print("4. ✅ Deliver Order")
                    print("5. 🧭 Navigation & GPS")
                    
                    print("\n📊 PERFORMANCE & REPORTS:")
                    print("6. 📈 View Performance")
                    
                    print("\n⚙️ SYSTEM:")
                    print("7. 🔓 Logout")
                    print("0. ❌ Exit")
                
                choice = input("\nSelect option: ").strip()
                
                if choice == '0':
                    if self.current_user:
                        self.logout()
                    self.print_info("Thank you for using E-commerce Delivery Portal!")
                    break
                elif choice == '1':
                    if not self.current_user:
                        if self.authenticate_delivery_personnel():
                            continue
                        else:
                            input("Press Enter to continue...")
                    else:
                        self.view_assigned_routes()
                elif choice == '2' and self.current_user:
                    self.start_route()
                elif choice == '3' and self.current_user:
                    self.view_route_orders()
                elif choice == '4' and self.current_user:
                    self.deliver_order()
                elif choice == '5' and self.current_user:
                    self.view_navigation_help()
                elif choice == '6' and self.current_user:
                    self.view_delivery_performance()
                elif choice == '7' and self.current_user:
                    self.logout()
                else:
                    if not self.current_user:
                        self.print_error("Please login first")
                    else:
                        self.print_error("Invalid option")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                self.print_info("\nOperation cancelled by user")
                break
            except Exception as e:
                self.print_error(f"System error: {str(e)}")
                input("Press Enter to continue...")

    def run(self):
        """Run the delivery portal"""
        try:
            self.clear_screen()
            self.print_header("AUTHENTICATION")
            
            print("🚚 Welcome to E-commerce Delivery Portal")
            print("Complete delivery management system for delivery personnel")
            print()
            print("🔐 Please authenticate to access the system")
            print("⚠️  Delivery personnel credentials required")
            print()
            print("🔑 DEFAULT TEST CREDENTIALS:")
            print("   🆔 Employee ID: EMP-001")
            print("   🔒 Password: password123")
            print("   (Note: Using existing staff member for testing)")
            print()
            print("⚠️  Note: Change default credentials in production!")
            print()
            print("🌟 FEATURES:")
            print("   • Route Management & GPS Navigation")
            print("   • Order Delivery & Status Tracking")
            print("   • COD Payment Collection")
            print("   • Delivery Proof & Customer Verification")
            print("   • Performance Analytics & Reporting")
            print("   • Real-time Issue Reporting")
            print()
            
            input("Press Enter to continue...")
            
            self.main_menu()
            
        except Exception as e:
            self.print_error(f"Failed to start delivery portal: {str(e)}")


def main():
    """Main function to run the delivery portal"""
    try:
        portal = DeliveryPortal()
        portal.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ System Error: {str(e)}")
        print("Please contact system administrator")


if __name__ == "__main__":
    main()
