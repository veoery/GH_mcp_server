import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerConfig:
    """Server configuration."""

    # Rhino/Grasshopper configuration
    rhino_path: Optional[str] = None  # Path to Rhino installation
    use_compute_api: bool = False  # Whether to use compute.rhino3d.com
    use_rhino3dm: bool = False  # Whether to use rhino3dm library
    compute_url: Optional[str] = None  # Compute API URL
    compute_api_key: Optional[str] = None  # Compute API key

    # Server configuration
    server_name: str = "Grasshopper MCP"
    server_port: int = 8080

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables."""
        use_compute = os.getenv("USE_COMPUTE_API", "false").lower() == "true"
        use_rhino3dm = os.getenv("USE_RHINO3DM", "true").lower() == "true"

        return cls(
            rhino_path=os.getenv("RHINO_PATH"),
            use_compute_api=use_compute,
            use_rhino3dm=use_rhino3dm,
            compute_url=os.getenv("COMPUTE_URL"),
            compute_api_key=os.getenv("COMPUTE_API_KEY"),
            server_name=os.getenv("SERVER_NAME", "Grasshopper MCP"),
            server_port=int(os.getenv("SERVER_PORT", "8080")),
        )
