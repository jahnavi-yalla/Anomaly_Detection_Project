#!/usr/bin/env python3
"""
Quick script to view all stored data in the database
"""
import sqlite3
from pathlib import Path

DB_PATH = "data/streamsight.db"

def view_data():
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    
    print("=" * 80)
    print("📊 DATABASE CONTENTS - StreamSight.db")
    print("=" * 80)
    
    for table in tables:
        table_name = table[0]
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        print(f"\n📋 TABLE: {table_name.upper()} ({count} records)")
        print("-" * 80)
        
        rows = cursor.execute(f"SELECT * FROM {table_name}").fetchall()
        
        if not rows:
            print("   (empty)")
            continue
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Print header
        print("  " + " | ".join(f"{col:20}" for col in columns))
        print("  " + "-" * (len(columns) * 22))
        
        # Print rows
        for row in rows:
            print("  " + " | ".join(f"{str(row[col])[:20]:20}" for col in columns))
    
    conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    view_data()
