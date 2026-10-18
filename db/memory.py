import sqlite3
import os
import json
import threading
from typing import Dict, List, Any, Tuple

class MemoryDB:
    def __init__(self, db_path="memory.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self._local = threading.local()
        self.setup_tables()
    
    def get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def get_cursor(self):
        """Get thread-local cursor"""
        if not hasattr(self._local, 'cursor') or self._local.cursor is None:
            self._local.cursor = self.get_connection().cursor()
        return self._local.cursor
    
    def connect(self):
        """Establish connection to SQLite database (for backwards compatibility)"""
        return self.get_connection(), self.get_cursor()
        
    def setup_tables(self):
        """Create necessary tables if they don't exist"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        # JD Summaries table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jd_summaries (
            id INTEGER PRIMARY KEY,
            job_title TEXT,
            required_skills TEXT,
            years_of_experience TEXT,
            education TEXT,
            certifications TEXT,
            responsibilities TEXT,
            raw_jd TEXT
        )
        ''')
        
        # CV Data table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cv_data (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            education TEXT,
            work_experience TEXT,
            skills TEXT,
            certifications TEXT,
            tech_stack TEXT,
            raw_text TEXT
        )
        ''')
        
        # Match Scores table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_scores (
            id INTEGER PRIMARY KEY,
            jd_id INTEGER,
            cv_id INTEGER,
            score REAL,
            FOREIGN KEY (jd_id) REFERENCES jd_summaries (id),
            FOREIGN KEY (cv_id) REFERENCES cv_data (id)
        )
        ''')
        
        # Shortlisted Candidates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shortlist (
            id INTEGER PRIMARY KEY,
            match_id INTEGER,
            jd_id INTEGER,
            cv_id INTEGER,
            score REAL,
            email_sent INTEGER DEFAULT 0,
            email_sent_date TEXT,
            FOREIGN KEY (match_id) REFERENCES match_scores (id),
            FOREIGN KEY (jd_id) REFERENCES jd_summaries (id),
            FOREIGN KEY (cv_id) REFERENCES cv_data (id)
        )
        ''')
        
        conn.commit()
    
    def _find_id(self, table: str, where: str, params: tuple):
        """Return the newest row id in `table` matching `where`, or None.

        (Newest, because databases created before upserts existed may hold duplicates.)
        """
        cursor = self.get_cursor()
        cursor.execute(f"SELECT id FROM {table} WHERE {where} ORDER BY id DESC LIMIT 1", params)
        row = cursor.fetchone()
        return row[0] if row else None

    def insert_jd_summary(self, job_title: str, data: Dict[str, Any]) -> int:
        """Insert JD summary into database"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        query = '''
        INSERT INTO jd_summaries 
        (job_title, required_skills, years_of_experience, education, certifications, responsibilities, raw_jd)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        update_query = '''
        UPDATE jd_summaries
        SET required_skills = ?, years_of_experience = ?, education = ?,
            certifications = ?, responsibilities = ?, raw_jd = ?
        WHERE id = ?
        '''
        
        # Convert lists to JSON strings, leave other types as-is
        required_skills = json.dumps(data.get('required_skills')) if isinstance(data.get('required_skills'), list) else data.get('required_skills', '')
        certifications = json.dumps(data.get('certifications')) if isinstance(data.get('certifications'), list) else data.get('certifications', '')
        responsibilities = json.dumps(data.get('responsibilities')) if isinstance(data.get('responsibilities'), list) else data.get('responsibilities', '')
        
        values = (
            required_skills,
            data.get('years_of_experience', ''),
            data.get('education', ''),
            certifications,
            responsibilities,
            data.get('raw_jd', '')
        )
        # Upsert: re-running the pipeline updates the existing row instead of duplicating it
        existing_id = self._find_id('jd_summaries', 'job_title = ?', (job_title,))
        if existing_id is not None:
            cursor.execute(update_query, values + (existing_id,))
            conn.commit()
            return existing_id

        cursor.execute(query, (job_title,) + values)
        conn.commit()
        return cursor.lastrowid
    
    def insert_cv_data(self, filename: str, data: Dict[str, Any]) -> int:
        """Insert CV data into database"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        query = '''
        INSERT INTO cv_data
        (filename, name, email, phone, education, work_experience, skills, certifications, tech_stack, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        # Convert lists to JSON strings, leave other types as-is
        skills = json.dumps(data.get('skills')) if isinstance(data.get('skills'), list) else data.get('skills', '')
        certifications = json.dumps(data.get('certifications')) if isinstance(data.get('certifications'), list) else data.get('certifications', '')
        tech_stack = json.dumps(data.get('tech_stack')) if isinstance(data.get('tech_stack'), list) else data.get('tech_stack', '')
        
        values = (
            data.get('name', ''),
            data.get('email', ''),
            data.get('phone', ''),
            data.get('education', ''),
            data.get('work_experience', ''),
            skills,
            certifications,
            tech_stack,
            data.get('raw_text', '')
        )
        # Upsert by filename so re-runs don't duplicate candidates
        existing_id = self._find_id('cv_data', 'filename = ?', (filename,))
        if existing_id is not None:
            cursor.execute('''
                UPDATE cv_data
                SET name = ?, email = ?, phone = ?, education = ?, work_experience = ?,
                    skills = ?, certifications = ?, tech_stack = ?, raw_text = ?
                WHERE id = ?
            ''', values + (existing_id,))
            conn.commit()
            return existing_id

        cursor.execute(query, (filename,) + values)
        conn.commit()
        return cursor.lastrowid
    
    def insert_match_score(self, jd_id: int, cv_id: int, score: float) -> int:
        """Insert match score between JD and CV"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        query = '''
        INSERT INTO match_scores
        (jd_id, cv_id, score)
        VALUES (?, ?, ?)
        '''
        existing_id = self._find_id('match_scores', 'jd_id = ? AND cv_id = ?', (jd_id, cv_id))
        if existing_id is not None:
            cursor.execute("UPDATE match_scores SET score = ? WHERE id = ?", (score, existing_id))
            conn.commit()
            return existing_id

        cursor.execute(query, (jd_id, cv_id, score))
        conn.commit()
        return cursor.lastrowid
    
    def insert_shortlisted(self, match_id: int, jd_id: int, cv_id: int, score: float) -> int:
        """Insert shortlisted candidate"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        query = '''
        INSERT INTO shortlist
        (match_id, jd_id, cv_id, score)
        VALUES (?, ?, ?, ?)
        '''
        # Keep email_sent / email_sent_date intact when a candidate is re-shortlisted
        existing_id = self._find_id('shortlist', 'match_id = ?', (match_id,))
        if existing_id is not None:
            cursor.execute("UPDATE shortlist SET score = ? WHERE id = ?", (score, existing_id))
            conn.commit()
            return existing_id

        cursor.execute(query, (match_id, jd_id, cv_id, score))
        conn.commit()
        return cursor.lastrowid
    
    def update_email_sent(self, shortlist_id: int, sent_date: str) -> None:
        """Update email sent status for shortlisted candidate"""
        conn = self.get_connection()
        cursor = self.get_cursor()
        
        query = '''
        UPDATE shortlist
        SET email_sent = 1, email_sent_date = ?
        WHERE id = ?
        '''
        cursor.execute(query, (sent_date, shortlist_id))
        conn.commit()
    
    def get_jd_summary(self, jd_id: int) -> Dict:
        """Get JD summary by ID"""
        cursor = self.get_cursor()
        
        query = "SELECT * FROM jd_summaries WHERE id = ?"
        cursor.execute(query, (jd_id,))
        result = cursor.fetchone()
        if not result:
            return None
            
        # Convert result to dict
        result_dict = dict(result)
        
        # Parse JSON fields back to Python objects
        try:
            if result_dict.get('required_skills'):
                result_dict['required_skills'] = json.loads(result_dict['required_skills'])
            if result_dict.get('certifications'):
                result_dict['certifications'] = json.loads(result_dict['certifications'])
            if result_dict.get('responsibilities'):
                result_dict['responsibilities'] = json.loads(result_dict['responsibilities'])
        except json.JSONDecodeError:
            pass  # Keep as string if not valid JSON
            
        return result_dict
    
    def get_cv_data(self, cv_id: int) -> Dict:
        """Get CV data by ID"""
        cursor = self.get_cursor()
        
        query = "SELECT * FROM cv_data WHERE id = ?"
        cursor.execute(query, (cv_id,))
        result = cursor.fetchone()
        if not result:
            return None
            
        # Convert result to dict
        result_dict = dict(result)
        
        # Parse JSON fields back to Python objects
        try:
            if result_dict.get('skills'):
                result_dict['skills'] = json.loads(result_dict['skills'])
            if result_dict.get('certifications'):
                result_dict['certifications'] = json.loads(result_dict['certifications'])
            if result_dict.get('tech_stack'):
                result_dict['tech_stack'] = json.loads(result_dict['tech_stack'])
        except json.JSONDecodeError:
            pass  # Keep as string if not valid JSON
            
        return result_dict
    
    def get_all_jds(self) -> List[Dict]:
        """Get all JD summaries"""
        cursor = self.get_cursor()
        
        query = "SELECT * FROM jd_summaries"
        cursor.execute(query)
        results = cursor.fetchall()
        
        processed_results = []
        for row in results:
            result_dict = dict(row)
            
            # Parse JSON fields back to Python objects
            try:
                if result_dict.get('required_skills'):
                    result_dict['required_skills'] = json.loads(result_dict['required_skills'])
                if result_dict.get('certifications'):
                    result_dict['certifications'] = json.loads(result_dict['certifications'])
                if result_dict.get('responsibilities'):
                    result_dict['responsibilities'] = json.loads(result_dict['responsibilities'])
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON
                
            processed_results.append(result_dict)
            
        return processed_results
    
    def get_all_cvs(self) -> List[Dict]:
        """Get all CV data"""
        cursor = self.get_cursor()
        
        query = "SELECT * FROM cv_data"
        cursor.execute(query)
        results = cursor.fetchall()
        
        processed_results = []
        for row in results:
            result_dict = dict(row)
            
            # Parse JSON fields back to Python objects
            try:
                if result_dict.get('skills'):
                    result_dict['skills'] = json.loads(result_dict['skills'])
                if result_dict.get('certifications'):
                    result_dict['certifications'] = json.loads(result_dict['certifications'])
                if result_dict.get('tech_stack'):
                    result_dict['tech_stack'] = json.loads(result_dict['tech_stack'])
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON
                
            processed_results.append(result_dict)
            
        return processed_results
    
    def get_shortlisted_candidates(self) -> List[Dict]:
        """Get all shortlisted candidates with related data"""
        cursor = self.get_cursor()
        
        query = '''
        SELECT s.*, j.job_title, j.required_skills, c.name, c.email, c.skills
        FROM shortlist s
        JOIN jd_summaries j ON s.jd_id = j.id
        JOIN cv_data c ON s.cv_id = c.id
        '''
        cursor.execute(query)
        results = cursor.fetchall()
        
        processed_results = []
        for row in results:
            result_dict = dict(row)
            
            # Parse JSON fields back to Python objects
            try:
                if result_dict.get('required_skills'):
                    result_dict['required_skills'] = json.loads(result_dict['required_skills'])
                if result_dict.get('skills'):
                    result_dict['skills'] = json.loads(result_dict['skills'])
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON
                
            processed_results.append(result_dict)
            
        return processed_results
    
    def get_pending_emails(self) -> List[Dict]:
        """Get shortlisted candidates where email hasn't been sent"""
        cursor = self.get_cursor()
        
        query = '''
        SELECT s.id as shortlist_id, s.score, j.job_title, j.required_skills,
               c.name, c.email, c.skills
        FROM shortlist s
        JOIN jd_summaries j ON s.jd_id = j.id
        JOIN cv_data c ON s.cv_id = c.id
        WHERE s.email_sent = 0
        '''
        cursor.execute(query)
        results = cursor.fetchall()
        
        processed_results = []
        for row in results:
            result_dict = dict(row)
            
            # Parse JSON fields back to Python objects
            try:
                if result_dict.get('required_skills'):
                    result_dict['required_skills'] = json.loads(result_dict['required_skills'])
                if result_dict.get('skills'):
                    result_dict['skills'] = json.loads(result_dict['skills'])
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON
                
            processed_results.append(result_dict)
            
        return processed_results
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            self._local.cursor = None 