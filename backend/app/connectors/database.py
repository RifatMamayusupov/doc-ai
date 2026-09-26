"""
Database Connector.

Provides integration with SQL databases for data extraction.

Supports:
- PostgreSQL
- MySQL
- SQLite
- Oracle (with cx_Oracle)
- SQL Server (with pyodbc)

Required credentials:
- dialect: Database dialect (postgresql, mysql, sqlite, oracle, mssql)
- host: Database host
- port: Database port
- database: Database name
- username: Database user
- password: Database password
- query or table: SQL query or table name to extract
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator
import csv
import io

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    FileInfo,
    ProgressCallback,
    SyncResult,
)
from .registry import register_connector


@register_connector(ConnectorType.DATABASE)
class DatabaseConnector(BaseConnector):
    """
    Connector for SQL databases.
    
    Extracts data from tables/queries and exports as CSV/JSON.
    Uses SQLAlchemy for database operations.
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._engine = None
        self._async_engine = None
    
    def _build_connection_string(self) -> str:
        """Build SQLAlchemy connection string from credentials."""
        dialect = self.config.credentials.get("dialect", "postgresql")
        host = self.config.credentials.get("host", "localhost")
        port = self.config.credentials.get("port")
        database = self.config.credentials.get("database", "")
        username = self.config.credentials.get("username", "")
        password = self.config.credentials.get("password", "")
        
        # Build URL
        if dialect == "sqlite":
            return f"sqlite:///{database}"
        
        # Map dialect to driver
        dialect_map = {
            "postgresql": "postgresql+asyncpg",
            "mysql": "mysql+aiomysql",
            "mssql": "mssql+pyodbc",
            "oracle": "oracle+cx_oracle",
        }
        
        driver = dialect_map.get(dialect, dialect)
        
        if port:
            return f"{driver}://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"{driver}://{username}:{password}@{host}/{database}"
    
    async def _ensure_engine(self):
        """Ensure we have a database engine."""
        if self._async_engine is None:
            try:
                from sqlalchemy.ext.asyncio import create_async_engine
                
                conn_string = self._build_connection_string()
                self._async_engine = create_async_engine(conn_string)
                
            except ImportError:
                # Fallback to sync engine
                from sqlalchemy import create_engine
                
                conn_string = self._build_connection_string()
                # Use sync dialect
                conn_string = conn_string.replace("+asyncpg", "").replace("+aiomysql", "")
                self._engine = create_engine(conn_string)
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the database connection."""
        try:
            await self._ensure_engine()
            
            if self._async_engine:
                async with self._async_engine.connect() as conn:
                    await conn.execute("SELECT 1")
            else:
                with self._engine.connect() as conn:
                    conn.execute("SELECT 1")
            
            self._is_connected = True
            database = self.config.credentials.get("database", "unknown")
            return True, f"Connected to database: {database}"
            
        except Exception as e:
            self._is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """
        List available tables as 'files'.
        
        In database context, tables are treated as files.
        """
        await self._ensure_engine()
        
        try:
            from sqlalchemy import inspect
            
            if self._async_engine:
                async with self._async_engine.connect() as conn:
                    # Run inspection in sync context
                    def get_tables(connection):
                        inspector = inspect(connection)
                        return inspector.get_table_names()
                    
                    tables = await conn.run_sync(get_tables)
            else:
                inspector = inspect(self._engine)
                tables = inspector.get_table_names()
            
            files = []
            for table_name in tables:
                # Get row count for size estimation
                row_count = await self._get_table_row_count(table_name)
                
                files.append(FileInfo(
                    id=table_name,
                    name=f"{table_name}.csv",
                    path=f"tables/{table_name}",
                    size=row_count * 100,  # Rough estimate
                    mime_type="text/csv",
                    metadata={
                        "type": "table",
                        "row_count": row_count,
                    },
                ))
            
            return files
            
        except Exception as e:
            print(f"Error listing tables: {e}")
            return []
    
    async def _get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count for a table."""
        try:
            from sqlalchemy import text
            
            query = text(f"SELECT COUNT(*) FROM {table_name}")
            
            if self._async_engine:
                async with self._async_engine.connect() as conn:
                    result = await conn.execute(query)
                    return result.scalar() or 0
            else:
                with self._engine.connect() as conn:
                    result = conn.execute(query)
                    return result.scalar() or 0
                    
        except Exception:
            return 0
    
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """Get info for a specific table."""
        table_name = file_id.replace(".csv", "").replace(".json", "")
        
        row_count = await self._get_table_row_count(table_name)
        
        return FileInfo(
            id=table_name,
            name=f"{table_name}.csv",
            path=f"tables/{table_name}",
            size=row_count * 100,
            mime_type="text/csv",
            metadata={
                "type": "table",
                "row_count": row_count,
            },
        )
    
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """Extract table data to a file."""
        try:
            table_name = file_id.replace(".csv", "").replace(".json", "")
            
            # Determine output format from target path
            output_format = "csv" if target_path.suffix == ".csv" else "json"
            
            await self._ensure_engine()
            
            from sqlalchemy import text
            
            query = text(f"SELECT * FROM {table_name}")
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self._async_engine:
                async with self._async_engine.connect() as conn:
                    result = await conn.execute(query)
                    columns = list(result.keys())
                    rows = result.fetchall()
            else:
                with self._engine.connect() as conn:
                    result = conn.execute(query)
                    columns = list(result.keys())
                    rows = result.fetchall()
            
            total_rows = len(rows)
            
            if output_format == "csv":
                with open(target_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    
                    for i, row in enumerate(rows):
                        writer.writerow(row)
                        
                        if on_progress and i % 1000 == 0:
                            progress = int((i / total_rows) * 100)
                            on_progress(progress, 100, f"Exporting: {table_name}")
            else:
                data = []
                for i, row in enumerate(rows):
                    data.append(dict(zip(columns, row)))
                    
                    if on_progress and i % 1000 == 0:
                        progress = int((i / total_rows) * 100)
                        on_progress(progress, 100, f"Exporting: {table_name}")
                
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            print(f"Database export error: {e}")
            return False
    
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """Stream table data as CSV."""
        table_name = file_id.replace(".csv", "").replace(".json", "")
        
        await self._ensure_engine()
        
        from sqlalchemy import text
        
        query = text(f"SELECT * FROM {table_name}")
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        if self._async_engine:
            async with self._async_engine.connect() as conn:
                result = await conn.execute(query)
                columns = list(result.keys())
                
                # Write header
                writer.writerow(columns)
                
                batch_size = 1000
                while True:
                    rows = result.fetchmany(batch_size)
                    if not rows:
                        break
                    
                    for row in rows:
                        writer.writerow(row)
                    
                    # Yield current buffer
                    data = output.getvalue().encode("utf-8")
                    if len(data) >= chunk_size:
                        yield data
                        output.truncate(0)
                        output.seek(0)
        
        # Yield remaining data
        remaining = output.getvalue().encode("utf-8")
        if remaining:
            yield remaining
    
    async def execute_query(
        self,
        query: str,
        parameters: dict | None = None,
    ) -> list[dict]:
        """
        Execute a custom SQL query.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        await self._ensure_engine()
        
        from sqlalchemy import text
        
        sql = text(query)
        
        if self._async_engine:
            async with self._async_engine.connect() as conn:
                result = await conn.execute(sql, parameters or {})
                columns = list(result.keys())
                rows = result.fetchall()
        else:
            with self._engine.connect() as conn:
                result = conn.execute(sql, parameters or {})
                columns = list(result.keys())
                rows = result.fetchall()
        
        return [dict(zip(columns, row)) for row in rows]
    
    async def get_schema(self, table_name: str) -> dict:
        """
        Get the schema for a table.
        
        Returns:
            Dictionary with column definitions
        """
        await self._ensure_engine()
        
        from sqlalchemy import inspect
        
        if self._async_engine:
            async with self._async_engine.connect() as conn:
                def get_columns(connection):
                    inspector = inspect(connection)
                    return inspector.get_columns(table_name)
                
                columns = await conn.run_sync(get_columns)
        else:
            inspector = inspect(self._engine)
            columns = inspector.get_columns(table_name)
        
        return {
            "table": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default")) if col.get("default") else None,
                }
                for col in columns
            ],
        }
    
    async def close(self):
        """Close the database connection."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._engine:
            self._engine.dispose()
        
        self._async_engine = None
        self._engine = None
        self._is_connected = False
