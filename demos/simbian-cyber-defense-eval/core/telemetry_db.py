"""High-performance in-memory telemetry database engine for threat hunting evaluations.

Supports querying security telemetry (Sysmon EventIDs 1, 3, 7, 8, 10, 11, 12, 13,
Windows Security EventIDs 4688, 4624, 4672, 4698, 7045, PowerShell 4104) via standard SQL.
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple
from .models import LogEvent


class TelemetryDatabase:
    """In-memory relational telemetry store for cybersecurity investigation."""

    def __init__(self, db_name: str = ":memory:"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self.query_history: List[Dict[str, Any]] = []

    def _init_tables(self) -> None:
        """Create structured tables and indexes optimized for SecOps threat hunting."""
        cursor = self.conn.cursor()

        # Primary unified events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                host TEXT NOT NULL,
                user TEXT NOT NULL,
                process_name TEXT,
                command_line TEXT,
                parent_process TEXT,
                parent_command_line TEXT,
                process_id INTEGER,
                parent_process_id INTEGER,
                ip_address TEXT,
                port INTEGER,
                file_path TEXT,
                registry_path TEXT,
                details_json TEXT,
                is_malicious INTEGER DEFAULT 0,
                ground_truth_rule TEXT
            )
        """)

        # Process creation view (Event ID 1 / 4688)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS process_creation AS
            SELECT id, timestamp, host, user, process_name, command_line,
                   parent_process, parent_command_line, process_id, parent_process_id
            FROM events
            WHERE event_id IN (1, 4104, 4688) OR (process_name IS NOT NULL AND process_name != '')
        """)

        # Network connections view (Event ID 3)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS network_connections AS
            SELECT id, timestamp, host, user, process_name, ip_address, port, command_line
            FROM events
            WHERE event_id = 3 OR ip_address IS NOT NULL
        """)

        # Registry / Persistence modifications view (Event ID 12, 13, 4698, 7045)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS persistence_events AS
            SELECT id, timestamp, host, user, process_name, registry_path, file_path, command_line
            FROM events
            WHERE event_id IN (11, 12, 13, 4698, 7045)
        """)

        # PowerShell ScriptBlock view (Event ID 4104)
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS powershell_scripts AS
            SELECT id, timestamp, host, user, process_name, command_line, details_json
            FROM events
            WHERE event_id = 4104 OR process_name LIKE '%powershell%'
        """)

        # Speed up threat hunting queries with indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_eid ON events(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_pname ON events(process_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_parent ON events(parent_process)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON events(user)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_ip ON events(ip_address)")
        self.conn.commit()

    def load_events(self, events: List[LogEvent]) -> int:
        """Bulk load log events into the telemetry database.

        Args:
            events (List[LogEvent]): A list of structured LogEvent objects to insert.

        Returns:
            int: The total number of events successfully inserted into the database.
        """
        cursor = self.conn.cursor()
        rows = [
            (
                e.id,
                e.timestamp,
                e.event_id,
                e.source,
                e.host,
                e.user,
                e.process_name,
                e.command_line,
                e.parent_process,
                e.parent_command_line,
                e.process_id,
                e.parent_process_id,
                e.ip_address,
                e.port,
                e.file_path,
                e.registry_path,
                json.dumps(e.details),
                1 if e.is_malicious else 0,
                e.ground_truth_rule,
            )
            for e in events
        ]

        cursor.executemany(
            """
            INSERT OR REPLACE INTO events (
                id, timestamp, event_id, source, host, user,
                process_name, command_line, parent_process, parent_command_line,
                process_id, parent_process_id, ip_address, port, file_path,
                registry_path, details_json, is_malicious, ground_truth_rule
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def execute_query(
        self, query: str, max_rows: int = 50, timeout_sec: float = 10.0
    ) -> Tuple[List[str], List[List[Any]], float, Optional[str]]:
        """Execute a read-only SQL query safely against sandbox telemetry tables.

        Args:
            query (str): The raw SQLite query string formulated by the agent.
            max_rows (int, optional): Maximum number of rows to return. Defaults to 50.
            timeout_sec (float, optional): Maximum execution time in seconds. Defaults to 10.0.

        Returns:
            Tuple[List[str], List[List[Any]], float, Optional[str]]: A 4-tuple containing:
                - List of column names (headers).
                - List of row records.
                - Execution duration in milliseconds.
                - Error string if execution failed or was rejected, else None.
        """
        start_time = time.perf_counter()
        clean_query = query.strip().rstrip(";")

        # Safety sanity check: Threat hunting evaluations are strictly read-only
        forbidden_keywords = ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "ATTACH ", "DETACH "]
        upper_q = clean_query.upper()
        for kw in forbidden_keywords:
            if upper_q.startswith(kw) or f" {kw}" in upper_q:
                duration = (time.perf_counter() - start_time) * 1000
                err_msg = f"Security Violation: Query contains forbidden modification keyword '{kw.strip()}'. Only SELECT queries are permitted."
                self.query_history.append({"query": query, "success": False, "error": err_msg, "duration_ms": duration})
                return [], [], duration, err_msg

        try:
            cursor = self.conn.cursor()
            cursor.execute(clean_query)
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchmany(max_rows)
            formatted_rows = [[item for item in row] for row in raw_rows]
            duration = (time.perf_counter() - start_time) * 1000

            self.query_history.append({
                "query": query,
                "success": True,
                "row_count": len(formatted_rows),
                "duration_ms": duration,
            })
            return col_names, formatted_rows, duration, None

        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            err_msg = f"SQLite Execution Error: {e}. Hint: Verify table names ('events', 'process_creation', 'network_connections') and use case-insensitive LIKE operators."
            self.query_history.append({"query": query, "success": False, "error": err_msg, "duration_ms": duration})
            return [], [], duration, err_msg

    def get_schema_summary(self) -> str:
        """Return a markdown schema summary for injection into the agent system prompt.

        Returns:
            str: Markdown documentation of available tables, views, columns, and sample queries.
        """
        return """
### Available Telemetry Tables and Views:

1. **`events`** (Primary unified log table)
   - `id` (INTEGER, Primary Key): Unique log identifier
   - `timestamp` (TEXT): ISO 8601 event timestamp
   - `event_id` (INTEGER): Sysmon/Windows Event ID (1=Process Create, 3=Network, 11=File Create, 12/13=Registry, 4104=ScriptBlock, 4688=Security Proc, 4698=Scheduled Task, 7045=Service Install)
   - `host` (TEXT): Machine hostname
   - `user` (TEXT): Account name
   - `process_name` (TEXT): Executable path / binary name
   - `command_line` (TEXT): Full command line arguments
   - `parent_process` (TEXT): Spawning process executable
   - `parent_command_line` (TEXT): Spawning process command line
   - `ip_address` (TEXT): Destination/Source IP address
   - `port` (INTEGER): Network port
   - `file_path` (TEXT): File created/modified
   - `registry_path` (TEXT): Registry key modified

2. **`process_creation`** (View for Event ID 1 / 4688)
3. **`network_connections`** (View for Event ID 3 network activity)
4. **`persistence_events`** (View for Event IDs 11, 12, 13, 4698, 7045)
5. **`powershell_scripts`** (View for PowerShell ScriptBlocks / 4104)

*Query Example*:
```sql
SELECT id, timestamp, user, process_name, command_line
FROM events
WHERE command_line LIKE '%powershell%' OR command_line LIKE '%certutil%'
ORDER BY timestamp ASC LIMIT 20;
```
""".strip()

    def get_total_events(self) -> int:
        """Get total event count in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        res = cursor.fetchone()
        return res[0] if res else 0

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
