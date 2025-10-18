"""
Persistent Build Storage - Replace in-memory storage with persistent storage
Technical Debt Item #1 from analysis
"""
import json
import sqlite3
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import threading


class PersistentBuildStorage:
    """
    Persistent storage for builds using SQLite
    Replaces in-memory dict with database storage
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(".sb_artifacts/builds.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS builds (
                    build_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    brief TEXT,
                    build_status TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    current_step TEXT,
                    app_url TEXT,
                    source_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    build_data TEXT  -- JSON blob for complete build state
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS build_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (build_id) REFERENCES builds(build_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS build_metrics (
                    build_id TEXT PRIMARY KEY,
                    duration_seconds REAL,
                    entity_count INTEGER,
                    file_count INTEGER,
                    validation_score INTEGER,
                    test_coverage INTEGER,
                    FOREIGN KEY (build_id) REFERENCES builds(build_id)
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_builds_status ON builds(build_status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_builds_created ON builds(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_build ON build_logs(build_id)')
            
            conn.commit()
    
    def save_build(self, build_id: str, build_data: Dict):
        """Save or update build"""
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                now = datetime.utcnow().isoformat() + "Z"
                
                # Check if build exists
                cursor = conn.execute('SELECT build_id FROM builds WHERE build_id = ?', (build_id,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    # Update existing
                    conn.execute('''
                        UPDATE builds SET
                            project_name = ?,
                            brief = ?,
                            build_status = ?,
                            progress = ?,
                            current_step = ?,
                            app_url = ?,
                            source_path = ?,
                            updated_at = ?,
                            completed_at = ?,
                            build_data = ?
                        WHERE build_id = ?
                    ''', (
                        build_data.get("project_name", ""),
                        build_data.get("brief", ""),
                        build_data.get("build_status", "building"),
                        build_data.get("progress", 0),
                        build_data.get("current_step", ""),
                        build_data.get("app_url", ""),
                        build_data.get("source_path", ""),
                        now,
                        now if build_data.get("build_status") in ["success", "failed"] else None,
                        json.dumps(build_data),
                        build_id
                    ))
                else:
                    # Insert new
                    conn.execute('''
                        INSERT INTO builds (
                            build_id, project_name, brief, build_status, progress,
                            current_step, app_url, source_path, created_at, updated_at, build_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        build_id,
                        build_data.get("project_name", ""),
                        build_data.get("brief", ""),
                        build_data.get("build_status", "building"),
                        build_data.get("progress", 0),
                        build_data.get("current_step", ""),
                        build_data.get("app_url", ""),
                        build_data.get("source_path", ""),
                        now,
                        now,
                        json.dumps(build_data)
                    ))
                
                conn.commit()
    
    def get_build(self, build_id: str) -> Optional[Dict]:
        """Get build by ID"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM builds WHERE build_id = ?', (build_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Parse build data
            build_data = json.loads(row['build_data']) if row['build_data'] else {}
            
            # Merge with structured fields
            return {
                **build_data,
                "build_id": row['build_id'],
                "project_name": row['project_name'],
                "build_status": row['build_status'],
                "progress": row['progress'],
                "current_step": row['current_step'],
                "app_url": row['app_url'],
                "source_path": row['source_path'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            }
    
    def list_builds(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """List builds with optional filtering"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            query = 'SELECT * FROM builds'
            params = []
            
            if status:
                query += ' WHERE build_status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            builds = []
            for row in rows:
                builds.append({
                    "build_id": row['build_id'],
                    "project_name": row['project_name'],
                    "build_status": row['build_status'],
                    "progress": row['progress'],
                    "current_step": row['current_step'],
                    "source_path": row['source_path'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                })
            
            return builds
    
    def delete_build(self, build_id: str) -> bool:
        """Delete build"""
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Delete logs
                conn.execute('DELETE FROM build_logs WHERE build_id = ?', (build_id,))
                
                # Delete metrics
                conn.execute('DELETE FROM build_metrics WHERE build_id = ?', (build_id,))
                
                # Delete build
                cursor = conn.execute('DELETE FROM builds WHERE build_id = ?', (build_id,))
                
                conn.commit()
                return cursor.rowcount > 0
    
    def add_log(self, build_id: str, level: str, message: str):
        """Add log entry for build"""
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT INTO build_logs (build_id, level, message, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (build_id, level, message, datetime.utcnow().isoformat() + "Z"))
                conn.commit()
    
    def get_logs(self, build_id: str, limit: int = 100) -> List[Dict]:
        """Get logs for build"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM build_logs
                WHERE build_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (build_id, limit))
            
            return [
                {
                    "level": row['level'],
                    "message": row['message'],
                    "timestamp": row['timestamp']
                }
                for row in cursor.fetchall()
            ]
    
    def save_metrics(self, build_id: str, metrics: Dict):
        """Save build metrics"""
        with self.lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO build_metrics (
                        build_id, duration_seconds, entity_count, file_count,
                        validation_score, test_coverage
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    build_id,
                    metrics.get("duration_seconds", 0),
                    metrics.get("entity_count", 0),
                    metrics.get("file_count", 0),
                    metrics.get("validation_score", 0),
                    metrics.get("test_coverage", 0)
                ))
                conn.commit()
    
    def get_metrics(self, build_id: str) -> Optional[Dict]:
        """Get build metrics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM build_metrics WHERE build_id = ?', (build_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "duration_seconds": row['duration_seconds'],
                "entity_count": row['entity_count'],
                "file_count": row['file_count'],
                "validation_score": row['validation_score'],
                "test_coverage": row['test_coverage']
            }
    
    def get_statistics(self) -> Dict:
        """Get storage statistics"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total builds
            cursor = conn.execute('SELECT COUNT(*) as count FROM builds')
            total = cursor.fetchone()['count']
            
            # By status
            cursor = conn.execute('''
                SELECT build_status, COUNT(*) as count
                FROM builds
                GROUP BY build_status
            ''')
            by_status = {row['build_status']: row['count'] for row in cursor.fetchall()}
            
            # Average duration
            cursor = conn.execute('SELECT AVG(duration_seconds) as avg FROM build_metrics')
            avg_duration = cursor.fetchone()['avg'] or 0
            
            # Success rate
            success_count = by_status.get('success', 0)
            success_rate = (success_count / total * 100) if total > 0 else 0
            
            return {
                "total_builds": total,
                "by_status": by_status,
                "success_rate": round(success_rate, 2),
                "average_duration_seconds": round(avg_duration, 2)
            }


# Global instance
_build_storage = None

def get_build_storage(db_path: Optional[Path] = None) -> PersistentBuildStorage:
    """Get or create global build storage"""
    global _build_storage
    if _build_storage is None:
        _build_storage = PersistentBuildStorage(db_path)
    return _build_storage
