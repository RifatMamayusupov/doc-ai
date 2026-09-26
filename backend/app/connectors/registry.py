"""
Connector Registry - manages available connectors and their instantiation.
"""

from typing import Type

from .base import BaseConnector, ConnectorConfig, ConnectorType


# Registry of connector classes
_connector_classes: dict[ConnectorType, Type[BaseConnector]] = {}


def register_connector(connector_type: ConnectorType):
    """
    Decorator to register a connector class.
    
    Usage:
        @register_connector(ConnectorType.SHAREPOINT)
        class SharePointConnector(BaseConnector):
            ...
    """
    def decorator(cls: Type[BaseConnector]):
        _connector_classes[connector_type] = cls
        return cls
    return decorator


def get_connector(config: ConnectorConfig) -> BaseConnector:
    """
    Get a connector instance for the given configuration.
    
    Args:
        config: Connector configuration
        
    Returns:
        Connector instance
        
    Raises:
        ValueError: If connector type is not supported
    """
    connector_cls = _connector_classes.get(config.connector_type)
    if connector_cls is None:
        raise ValueError(f"Unsupported connector type: {config.connector_type}")
    
    return connector_cls(config)


def list_available_connectors() -> list[dict]:
    """
    List all available connector types.
    
    Returns:
        List of connector info dictionaries
    """
    return [
        {
            "type": ct.value,
            "name": ct.name.replace("_", " ").title(),
            "available": ct in _connector_classes,
        }
        for ct in ConnectorType
    ]


class ConnectorRegistry:
    """
    Registry for managing connector instances.
    
    This class maintains active connector instances and provides
    methods for creating, retrieving, and managing connectors.
    """
    
    def __init__(self):
        self._instances: dict[str, BaseConnector] = {}
    
    def create(self, config: ConnectorConfig) -> BaseConnector:
        """
        Create and register a new connector instance.
        
        Args:
            config: Connector configuration
            
        Returns:
            Connector instance
        """
        connector = get_connector(config)
        self._instances[config.id] = connector
        return connector
    
    def get(self, connector_id: str) -> BaseConnector | None:
        """
        Get a connector instance by ID.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            Connector instance or None
        """
        return self._instances.get(connector_id)
    
    def remove(self, connector_id: str) -> bool:
        """
        Remove a connector instance.
        
        Args:
            connector_id: Connector ID
            
        Returns:
            True if removed, False if not found
        """
        if connector_id in self._instances:
            del self._instances[connector_id]
            return True
        return False
    
    async def close_all(self):
        """Close all connector instances."""
        for connector in self._instances.values():
            await connector.close()
        self._instances.clear()
    
    def list_all(self) -> list[str]:
        """List all registered connector IDs."""
        return list(self._instances.keys())


# Global registry instance
registry = ConnectorRegistry()
