"""
Migration Script: Add role column to guests table

This script:
1. Adds a 'role' column to the guests table with default value 'residence'
2. Migrates existing role data from guest_roles table to the new column
3. Updates all guests without a role to 'residence'
"""

import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_connection


def migrate_add_role_column():
    """Add guest_type column to guests table and migrate data"""
    
    print("\n" + "="*70)
    print("🔄 MIGRATION: Adding 'guest_type' column to guests table")
    print("="*70 + "\n")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if guest_type column already exists
        cur.execute("PRAGMA table_info(guests)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'guest_type' in columns:
            print("⚠️  Column 'guest_type' already exists in guests table!")
            print("Checking data consistency...\n")
        else:
            print("📝 Step 1: Adding 'guest_type' column to guests table...")
            # Add guest_type column with default value 'Resident'
            cur.execute("""
                ALTER TABLE guests 
                ADD COLUMN guest_type TEXT DEFAULT 'Resident' 
                CHECK(guest_type IN ('Owner', 'Employee', 'Resident', 'Others'))
            """)
            print("✅ Column 'guest_type' added successfully!\n")
        
        # Migrate data from guest_roles to guests.guest_type
        print("📝 Step 2: Migrating role data from guest_roles table...")
        
        cur.execute("""
            SELECT g.guest_id, g.name, r.role_name, g.guest_type
            FROM guests g
            LEFT JOIN guest_roles gr ON gr.guest_id = g.guest_id
            LEFT JOIN roles r ON r.role_id = gr.role_id
        """)
        
        guests = cur.fetchall()
        updated_count = 0
        
        for guest in guests:
            guest_id, name, role_from_table, current_guest_type = guest
            
            # Map role_name to capitalized guest_type
            role_mapping = {
                'owner': 'Owner',
                'employee': 'Employee',
                'residence': 'Resident'
            }
            
            # If guest has a role in guest_roles but not in guests.guest_type
            if role_from_table and (not current_guest_type or current_guest_type == 'Resident'):
                mapped_type = role_mapping.get(role_from_table.lower(), 'Resident')
                if mapped_type != current_guest_type:
                    cur.execute(
                        "UPDATE guests SET guest_type = ? WHERE guest_id = ?",
                        (mapped_type, guest_id)
                    )
                    updated_count += 1
                    print(f"  ✓ Updated {name} ({guest_id}) to guest_type: {mapped_type}")
        
        if updated_count > 0:
            print(f"\n✅ Migrated {updated_count} guest role(s) successfully!\n")
        else:
            print("✅ No role migration needed (all guests already have guest_type)\n")
        
        # Set default 'Resident' for any guests without a guest_type
        print("📝 Step 3: Setting default 'Resident' guest_type for guests without guest_type...")
        
        cur.execute("""
            UPDATE guests 
            SET guest_type = 'Resident' 
            WHERE guest_type IS NULL OR guest_type = ''
        """)
        
        default_count = cur.rowcount
        if default_count > 0:
            print(f"✅ Set 'Resident' as default guest_type for {default_count} guest(s)\n")
        else:
            print("✅ All guests already have guest_type assigned\n")
        
        # Verify the migration
        print("📝 Step 4: Verifying migration...")
        
        cur.execute("""
            SELECT guest_type, COUNT(*) as count
            FROM guests
            GROUP BY guest_type
            ORDER BY 
                CASE guest_type
                    WHEN 'Owner' THEN 1
                    WHEN 'Employee' THEN 2
                    WHEN 'Resident' THEN 3
                    WHEN 'Others' THEN 4
                    ELSE 5
                END
        """)
        
        role_counts = cur.fetchall()
        
        print("\n" + "-"*70)
        print("Guest Type Distribution in Guests Table:")
        print("-"*70)
        
        total = 0
        for guest_type, count in role_counts:
            print(f"  {guest_type.upper():<15} : {count} guest(s)")
            total += count
        
        print("-"*70)
        print(f"  {'TOTAL':<15} : {total} guest(s)")
        print("-"*70)
        
        # Commit changes
        conn.commit()
        
        print("\n" + "="*70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\n💡 Next Steps:")
        print("  1. Update your application code to use guests.guest_type instead of guest_roles")
        print("  2. You can now optionally drop the guest_roles table if no longer needed")
        print("  3. Test the authentication system with the new guest_type column")
        print("\n")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n❌ Migration Error: {e}")
        print("Rolling back changes...\n")
        return False
    
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Unexpected Error: {e}")
        print("Rolling back changes...\n")
        return False
    
    finally:
        conn.close()
    
    return True


if __name__ == "__main__":
    try:
        success = migrate_add_role_column()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
