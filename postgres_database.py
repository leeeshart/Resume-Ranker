import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import contextlib

class PostgreSQLDatabase:
    """PostgreSQL database manager for the resume analysis system"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Job descriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_descriptions (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    parsed_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            ''')
            
            # Resume analyses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resume_analyses (
                    id SERIAL PRIMARY KEY,
                    job_id INTEGER NOT NULL REFERENCES job_descriptions(id),
                    resume_filename TEXT NOT NULL,
                    resume_text TEXT NOT NULL,
                    analysis_result JSONB NOT NULL,
                    relevance_score INTEGER NOT NULL,
                    verdict TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Audit log table for tracking changes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    old_values JSONB,
                    new_values JSONB,
                    user_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_active ON job_descriptions (is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_location ON job_descriptions (location)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_company ON job_descriptions (company)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_job ON resume_analyses (job_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_score ON resume_analyses (relevance_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_verdict ON resume_analyses (verdict)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_date ON resume_analyses (created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_filename ON resume_analyses (resume_filename)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_logs (table_name, record_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs (timestamp)')
            
            conn.commit()
    
    @contextlib.contextmanager
    def get_connection(self):
        """Get database connection with proper closing"""
        conn = psycopg2.connect(self.database_url)
        conn.autocommit = False
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()
    
    def _log_audit(self, conn, table_name: str, record_id: int, action: str, 
                   old_values: Optional[Dict] = None, new_values: Optional[Dict] = None):
        """Log audit trail for database changes"""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            table_name, 
            record_id, 
            action, 
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None
        ))
    
    def store_job_description(self, title: str, company: str, location: str, 
                            description: str, parsed_data: Dict) -> int:
        """Store job description and return job ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO job_descriptions (title, company, location, description, parsed_data)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (title, company, location, description, json.dumps(parsed_data)))
            
            job_id = cursor.fetchone()[0]
            
            # Log audit trail
            self._log_audit(conn, 'job_descriptions', job_id, 'INSERT', 
                          new_values={'title': title, 'company': company, 'location': location})
            
            return job_id
    
    def store_analysis_result(self, job_id: int, resume_filename: str, 
                            resume_text: str, analysis_result: Dict) -> int:
        """Store resume analysis result and return analysis ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO resume_analyses 
                (job_id, resume_filename, resume_text, analysis_result, relevance_score, verdict)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                job_id,
                resume_filename,
                resume_text,
                json.dumps(analysis_result),
                analysis_result.get('relevance_score', 0),
                analysis_result.get('verdict', 'Low')
            ))
            
            analysis_id = cursor.fetchone()[0]
            
            # Log audit trail
            self._log_audit(conn, 'resume_analyses', analysis_id, 'INSERT',
                          new_values={
                              'job_id': job_id, 
                              'resume_filename': resume_filename, 
                              'verdict': analysis_result.get('verdict', 'Low'),
                              'relevance_score': analysis_result.get('relevance_score', 0)
                          })
            
            return analysis_id
    
    def get_active_jobs(self) -> List[Dict]:
        """Get all active job descriptions"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT j.*, COUNT(r.id) as application_count
                FROM job_descriptions j
                LEFT JOIN resume_analyses r ON j.id = r.job_id
                WHERE j.is_active = true
                GROUP BY j.id
                ORDER BY j.created_at DESC
            ''')
            
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job['parsed_data'] = job['parsed_data']  # Already parsed as JSONB
                jobs.append(job)
            
            return jobs
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get job description by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM job_descriptions WHERE id = %s AND is_active = true
            ''', (job_id,))
            
            row = cursor.fetchone()
            if row:
                job = dict(row)
                job['parsed_data'] = job['parsed_data']  # Already parsed as JSONB
                return job
            
            return None
    
    def get_recent_analyses(self, job_id: int, limit: int = 10) -> List[Dict]:
        """Get recent analyses for a job"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT * FROM resume_analyses 
                WHERE job_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (job_id, limit))
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                analysis['analysis_result'] = analysis['analysis_result']  # Already parsed as JSONB
                analyses.append(analysis)
            
            return analyses
    
    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get dashboard statistics"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Active jobs count
            cursor.execute('SELECT COUNT(*) FROM job_descriptions WHERE is_active = true')
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
                WHERE created_at >= %s
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
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
                WHERE j.is_active = true
                GROUP BY j.id
                HAVING COUNT(r.id) > 0
                ORDER BY avg_score DESC
            ''')
            
            stats = []
            for row in cursor.fetchall():
                stat = dict(row)
                stat['avg_score'] = round(float(stat['avg_score']), 1) if stat['avg_score'] else 0
                stats.append(stat)
            
            return stats
    
    def get_candidates_by_job(self, job_id: int) -> List[Dict]:
        """Get all candidates for a specific job"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT 
                    resume_filename,
                    relevance_score,
                    verdict,
                    created_at
                FROM resume_analyses
                WHERE job_id = %s
                ORDER BY relevance_score DESC
            ''', (job_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_applications_over_time(self, days: int = 30) -> List[Dict]:
        """Get application counts over time"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM resume_analyses
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (days,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_score_distribution(self) -> List[Dict]:
        """Get score distribution"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT 
                    j.location,
                    COUNT(r.id) as applications,
                    AVG(r.relevance_score) as avg_score,
                    SUM(CASE WHEN r.verdict = 'High' THEN 1 ELSE 0 END) as high_suitability
                FROM job_descriptions j
                LEFT JOIN resume_analyses r ON j.id = r.job_id
                WHERE j.is_active = true
                GROUP BY j.location
                HAVING COUNT(r.id) > 0
                ORDER BY applications DESC
            ''')
            
            stats = []
            for row in cursor.fetchall():
                stat = dict(row)
                stat['avg_score'] = round(float(stat['avg_score']), 1) if stat['avg_score'] else 0
                stats.append(stat)
            
            return stats
    
    def search_analyses(self, query: str = "", job_id: Optional[int] = None, 
                       min_score: Optional[int] = None, verdict: Optional[str] = None,
                       location: Optional[str] = None, skills: Optional[List[str]] = None,
                       date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> List[Dict]:
        """Advanced search analyses with multiple filters"""
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(resume_filename ILIKE %s OR resume_text ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if job_id:
            conditions.append("job_id = %s")
            params.append(job_id)
        
        if min_score is not None:
            conditions.append("relevance_score >= %s")
            params.append(min_score)
        
        if verdict:
            conditions.append("verdict = %s")
            params.append(verdict)
            
        if location:
            conditions.append("j.location = %s")
            params.append(location)
            
        if skills:
            # Search for skills in the analysis result JSON
            skill_conditions = []
            for skill in skills:
                skill_conditions.append("(analysis_result::text ILIKE %s)")
                params.append(f"%{skill}%")
            if skill_conditions:
                conditions.append(f"({' OR '.join(skill_conditions)})")
        
        if date_from:
            conditions.append("r.created_at >= %s")
            params.append(date_from)
            
        if date_to:
            conditions.append("r.created_at <= %s")
            params.append(date_to)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute(f'''
                SELECT r.*, j.title as job_title, j.company, j.location as job_location
                FROM resume_analyses r
                JOIN job_descriptions j ON r.job_id = j.id
                WHERE {where_clause}
                ORDER BY r.created_at DESC
                LIMIT 100
            ''', params)
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                analysis['analysis_result'] = analysis['analysis_result']  # Already parsed as JSONB
                analyses.append(analysis)
            
            return analyses
    
    def get_high_scoring_candidates(self, min_score: int = 75) -> List[Dict]:
        """Get high-scoring candidates for email notifications"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute('''
                SELECT 
                    r.*,
                    j.title as job_title,
                    j.company,
                    j.location as job_location
                FROM resume_analyses r
                JOIN job_descriptions j ON r.job_id = j.id
                WHERE r.relevance_score >= %s
                AND r.created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                ORDER BY r.relevance_score DESC, r.created_at DESC
            ''', (min_score,))
            
            candidates = []
            for row in cursor.fetchall():
                candidate = dict(row)
                candidate['analysis_result'] = candidate['analysis_result']  # Already parsed as JSONB
                candidates.append(candidate)
            
            return candidates
    
    def deactivate_job(self, job_id: int) -> bool:
        """Deactivate a job description"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get old values for audit
            cursor.execute('SELECT is_active FROM job_descriptions WHERE id = %s', (job_id,))
            old_active = cursor.fetchone()
            
            cursor.execute('''
                UPDATE job_descriptions 
                SET is_active = false 
                WHERE id = %s
            ''', (job_id,))
            
            if cursor.rowcount > 0 and old_active:
                self._log_audit(conn, 'job_descriptions', job_id, 'UPDATE',
                              old_values={'is_active': old_active[0]},
                              new_values={'is_active': False})
                return True
            
            return False
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis result"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get old values for audit
            cursor.execute('SELECT resume_filename, verdict FROM resume_analyses WHERE id = %s', (analysis_id,))
            old_values = cursor.fetchone()
            
            cursor.execute('DELETE FROM resume_analyses WHERE id = %s', (analysis_id,))
            
            if cursor.rowcount > 0 and old_values:
                self._log_audit(conn, 'resume_analyses', analysis_id, 'DELETE',
                              old_values={'resume_filename': old_values[0], 'verdict': old_values[1]})
                return True
            
            return False