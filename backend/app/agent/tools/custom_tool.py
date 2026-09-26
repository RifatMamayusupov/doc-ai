from langchain_core.tools import tool

@tool
def check_server_status(service_name: str) -> str:
    """
    Check the status of a specific server service.
    
    Args:
        service_name: Name of the service (e.g., "database", "api", "frontend")
    """
    # Bu yerda haqiqiy logika bo'lishi mumkin (masalan API call)
    # Hozircha shunchaki mock javob qaytaramiz
    
    services = {
        "database": "Online (Latency: 15ms)",
        "api": "Online (Uptime: 99.9%)",
        "frontend": "Maintenance Mode",
        "payment": "Offline (Error 503)"
    }
    
    status = services.get(service_name.lower())
    if status:
        return f"Service '{service_name}' status: {status}"
    else:
        return f"Unknown service: '{service_name}'. Available: {', '.join(services.keys())}"
