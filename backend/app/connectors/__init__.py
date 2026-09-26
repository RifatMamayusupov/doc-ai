"""
Data Source Connectors Package.

This package provides connectors for various data sources:
- SharePoint / Office 365
- Google Drive
- AWS S3 / Azure Blob Storage
- Databases (PostgreSQL, MySQL, Oracle)
"""

from .base import BaseConnector, ConnectorConfig, SyncResult, FileInfo, ConnectorType
from .registry import ConnectorRegistry, get_connector, registry, list_available_connectors

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "SyncResult",
    "FileInfo",
    "ConnectorType",
    "ConnectorRegistry",
    "get_connector",
    "registry",
    "list_available_connectors",
]

