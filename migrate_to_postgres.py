#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL
"""

import sqlite3
import json
from postgres_database import PostgreSQLDatabase
from database import Database

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    
    print("Starting migration from SQLite to PostgreSQL...")
    
    # Initialize databases
    sqlite_db = Database()
    postgres_db = PostgreSQLDatabase()
    
    print("Databases initialized successfully.")
    
    # Migrate job descriptions
    print("Migrating job descriptions...")
    sqlite_jobs = sqlite_db.get_active_jobs()
    job_id_mapping = {}  # Map old IDs to new IDs
    
    for job in sqlite_jobs:
        print(f"Migrating job: {job['title']} - {job['company']}")
        
        new_job_id = postgres_db.store_job_description(
            title=job['title'],
            company=job['company'],
            location=job['location'],
            description=job['description'],
            parsed_data=job['parsed_data']
        )
        
        job_id_mapping[job['id']] = new_job_id
        print(f"Job migrated: {job['id']} -> {new_job_id}")
    
    print(f"Migrated {len(sqlite_jobs)} job descriptions.")
    
    # Migrate resume analyses
    print("Migrating resume analyses...")
    
    # Get all analyses from SQLite
    with sqlite_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM resume_analyses ORDER BY created_at')
        analyses = [dict(row) for row in cursor.fetchall()]
    
    migrated_analyses = 0
    for analysis in analyses:
        old_job_id = analysis['job_id']
        
        # Skip if job wasn't migrated
        if old_job_id not in job_id_mapping:
            print(f"Skipping analysis {analysis['id']} - job {old_job_id} not found")
            continue
        
        new_job_id = job_id_mapping[old_job_id]
        
        try:
            analysis_result = json.loads(analysis['analysis_result'])
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in analysis {analysis['id']}, skipping")
            continue
        
        new_analysis_id = postgres_db.store_analysis_result(
            job_id=new_job_id,
            resume_filename=analysis['resume_filename'],
            resume_text=analysis['resume_text'],
            analysis_result=analysis_result
        )
        
        migrated_analyses += 1
        print(f"Analysis migrated: {analysis['id']} -> {new_analysis_id}")
    
    print(f"Migrated {migrated_analyses} resume analyses.")
    
    # Verify migration
    print("\nVerifying migration...")
    postgres_stats = postgres_db.get_dashboard_stats()
    print(f"PostgreSQL stats: {postgres_stats}")
    
    print("Migration completed successfully!")
    return True

if __name__ == "__main__":
    try:
        migrate_data()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()