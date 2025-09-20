import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import contextlib

class Database:
    """SQLite database manager for the resume analysis system"""
    
    def __init__(self, db_path: str = "resume_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Job descriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    parsed_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Resume analyses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resume_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    resume_filename TEXT NOT NULL,
                    resume_text TEXT NOT NULL,
                    analysis_result TEXT NOT NULL,
                    relevance_score INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES job_descriptions (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_active ON job_descriptions (is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_job ON resume_analyses (job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_score ON resume_analyses (relevance_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_verdict ON resume_analyses (verdict)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_date ON resume_analyses (created_at)')
            
            conn.commit()
    
    @contextlib.contextmanager
    def get_connection(self):
        """Get database connection with proper closing"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def store_job_description(self, title: str, company: str, location: str, 
                            description: str, parsed_data: Dict) -> int:
        """Store job description and return job ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO job_descriptions (title, company, location, description, parsed_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, company, location, description, json.dumps(parsed_data)))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def store_analysis_result(self, job_id: int, resume_filename: str, 
                            resume_text: str, analysis_result: Dict) -> int:
        """Store resume analysis result and return analysis ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO resume_analyses 
                (job_id, resume_filename, resume_text, analysis_result, relevance_score, verdict)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                resume_filename,
                resume_text,
                json.dumps(analysis_result),
                analysis_result.get('relevance_score', 0),
                analysis_result.get('verdict', 'Low')
            ))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def get_active_jobs(self) -> List[Dict]:
        """Get all active job descriptions"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT j.*, COUNT(r.id) as application_count
                FROM job_descriptions j
                LEFT JOIN resume_analyses r ON j.id = r.job_id
                WHERE j.is_active = 1
                GROUP BY j.id
                ORDER BY j.created_at DESC
            ''')
            
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job['parsed_data'] = json.loads(job['parsed_data'])
                jobs.append(job)
            
            return jobs
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get job description by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM job_descriptions WHERE id = ? AND is_active = 1
            ''', (job_id,))
            
            row = cursor.fetchone()
            if row:
                job = dict(row)
                job['parsed_data'] = json.loads(job['parsed_data'])
                return job
            
            return None
    
    def get_recent_analyses(self, job_id: int, limit: int = 10) -> List[Dict]:
        """Get recent analyses for a job"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM resume_analyses 
                WHERE job_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (job_id, limit))
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                analysis['analysis_result'] = json.loads(analysis['analysis_result'])
                analyses.append(analysis)
            
            return analyses
    
    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get dashboard statistics"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Active jobs count
            cursor.execute('SELECT COUNT(*) FROM job_descriptions WHERE is_active = 1')
            active_jobs = cursor.fetchone()[0]
            
            # Total analyses count
            cursor.execute('SELECT COUNT(*) FROM resume_analyses')
            total_analyses = cursor.fetchone()[0]
            
            # High suitability count
            cursor.execute("SELECT COUNT(*) FROM resume_analyses WHERE verdict = 'High'")
            high_suitability = cursor.fetchone()[0]
            
            # This week analyses
            week_ago = datetime.now() - timedelta(days=7)
            cursor.execute('''
                SELECT COUNT(*) FROM resume_analyses 
                WHERE created_at >= ?
            ''', (week_ago,))
            this_week_analyses = cursor.fetchone()[0]
            
            return {
                'active_jobs': active_jobs,
                'total_analyses': total_analyses,
                'high_suitability': high_suitability,
                'this_week_analyses': this_week_analyses
            }
    
    def get_job_analysis_stats(self) -> List[Dict]:
        """Get analysis statistics by job"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    j.id,
                    j.title,
                    j.company,
                    j.location,
                    COUNT(r.id) as total_applications,
                    SUM(CASE WHEN r.verdict = 'High' THEN 1 ELSE 0 END) as high_suitability,
                    AVG(r.relevance_score) as avg_score
                FROM job_descriptions j
                LEFT JOIN resume_analyses r ON j.id = r.job_id
                WHERE j.is_active = 1
                GROUP BY j.id
                HAVING COUNT(r.id) > 0
                ORDER BY avg_score DESC
            ''')
            
            stats = []
            for row in cursor.fetchall():
                stat = dict(row)
                stat['avg_score'] = round(stat['avg_score'], 1) if stat['avg_score'] else 0
                stats.append(stat)
            
            return stats
    
    def get_candidates_by_job(self, job_id: int) -> List[Dict]:
        """Get all candidates for a specific job"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    resume_filename,
                    relevance_score,
                    verdict,
                    created_at
                FROM resume_analyses
                WHERE job_id = ?
                ORDER BY relevance_score DESC
            ''', (job_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_applications_over_time(self, days: int = 30) -> List[Dict]:
        """Get application counts over time"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM resume_analyses
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (days,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_score_distribution(self) -> List[Dict]:
        """Get score distribution"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN relevance_score >= 80 THEN '80-100'
                        WHEN relevance_score >= 60 THEN '60-79'
                        WHEN relevance_score >= 40 THEN '40-59'
                        WHEN relevance_score >= 20 THEN '20-39'
                        ELSE '0-19'
                    END as score_range,
                    COUNT(*) as count
                FROM resume_analyses
                GROUP BY 
                    CASE 
                        WHEN relevance_score >= 80 THEN '80-100'
                        WHEN relevance_score >= 60 THEN '60-79'
                        WHEN relevance_score >= 40 THEN '40-59'
                        WHEN relevance_score >= 20 THEN '20-39'
                        ELSE '0-19'
                    END
                ORDER BY score_range DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_location_stats(self) -> List[Dict]:
        """Get statistics by location"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    j.location,
                    COUNT(r.id) as applications,
                    AVG(r.relevance_score) as avg_score,
                    SUM(CASE WHEN r.verdict = 'High' THEN 1 ELSE 0 END) as high_suitability
                FROM job_descriptions j
                LEFT JOIN resume_analyses r ON j.id = r.job_id
                WHERE j.is_active = 1
                GROUP BY j.location
                HAVING COUNT(r.id) > 0
                ORDER BY applications DESC
            ''')
            
            stats = []
            for row in cursor.fetchall():
                stat = dict(row)
                stat['avg_score'] = round(stat['avg_score'], 1) if stat['avg_score'] else 0
                stats.append(stat)
            
            return stats
    
    def deactivate_job(self, job_id: int) -> bool:
        """Deactivate a job description"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE job_descriptions 
                SET is_active = 0 
                WHERE id = ?
            ''', (job_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis result"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM resume_analyses WHERE id = ?', (analysis_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def search_analyses(self, query: str, job_id: Optional[int] = None, 
                       min_score: Optional[int] = None, verdict: Optional[str] = None) -> List[Dict]:
        """Search analyses with filters"""
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(resume_filename LIKE ? OR resume_text LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if job_id:
            conditions.append("job_id = ?")
            params.append(job_id)
        
        if min_score is not None:
            conditions.append("relevance_score >= ?")
            params.append(min_score)
        
        if verdict:
            conditions.append("verdict = ?")
            params.append(verdict)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT r.*, j.title as job_title, j.company
                FROM resume_analyses r
                JOIN job_descriptions j ON r.job_id = j.id
                WHERE {where_clause}
                ORDER BY r.created_at DESC
                LIMIT 100
            ''', params)
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                analysis['analysis_result'] = json.loads(analysis['analysis_result'])
                analyses.append(analysis)
            
            return analyses
