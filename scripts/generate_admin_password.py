#!/usr/bin/env python3
"""
Password Hash Generator for Admin Authentication

This script helps you generate SHA256 hashes for admin passwords.
"""

import hashlib
import getpass

def generate_password_hash(password):
    """Generate SHA256 hash for a password"""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("🔐 Admin Password Hash Generator")
    print("=" * 35)
    
    while True:
        print("\nChoose an option:")
        print("1. Generate hash for a new password")
        print("2. Verify a password against a hash")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            # Generate new hash
            print("\n📝 Generate Password Hash:")
            password = getpass.getpass("Enter your new admin password: ")
            
            if not password:
                print("❌ Password cannot be empty!")
                continue
            
            hash_value = generate_password_hash(password)
            
            print(f"\n✅ Password Hash Generated:")
            print(f"Password: {password}")
            print(f"Hash: {hash_value}")
            print(f"\n🔧 Add this to your .env file:")
            print(f"ADMIN_PASSWORD_HASH={hash_value}")
            
        elif choice == '2':
            # Verify password
            print("\n🔍 Verify Password:")
            password = getpass.getpass("Enter password to verify: ")
            existing_hash = input("Enter existing hash: ").strip()
            
            calculated_hash = generate_password_hash(password)
            
            if calculated_hash == existing_hash:
                print("✅ Password matches the hash!")
            else:
                print("❌ Password does not match the hash!")
            
        elif choice == '3':
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
