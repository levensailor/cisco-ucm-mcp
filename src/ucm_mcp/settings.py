"""Environment-driven settings for the UCM MCP server."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CUCM connection and safety gates loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ucm_host: str = Field(default="", description="CUCM hostname or IP")
    ucm_username: str = Field(default="", description="Application user username")
    ucm_password: str = Field(default="", description="Application user password")
    ucm_version: str = Field(default="15.0", description="AXL schema version")
    ucm_port: int = Field(default=8443, description="CUCM HTTPS port")
    ucm_verify_ssl: bool = Field(default=False, description="Verify TLS certificates")

    ucm_allow_writes: bool = Field(
        default=False, description="Allow mutating AXL operations"
    )
    ucm_allow_service_control: bool = Field(
        default=False, description="Allow start/stop/restart/activate/deactivate"
    )
    ucm_allow_phone_execute: bool = Field(
        default=False, description="Allow phone CGI Execute / ITL macros"
    )

    phone_username: str = Field(default="", description="Phone web / CGI username")
    phone_password: str = Field(default="", description="Phone web / CGI password")

    ucm_transport: str = Field(default="stdio", description="stdio or http")
    ucm_http_host: str = Field(default="127.0.0.1")
    ucm_http_port: int = Field(default=8000)

    ucm_log_dir: str = Field(default="logs")
    ucm_log_level: str = Field(default="INFO")
    ucm_request_timeout: int = Field(default=30, description="HTTP/SOAP timeout seconds")
    ucm_download_max_bytes: int = Field(
        default=2 * 1024 * 1024, description="Max log/CDR download size"
    )

    def require_connection(self) -> None:
        """Raise if required CUCM connection settings are missing."""
        missing = [
            name
            for name, value in (
                ("UCM_HOST", self.ucm_host),
                ("UCM_USERNAME", self.ucm_username),
                ("UCM_PASSWORD", self.ucm_password),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"Missing required settings: {', '.join(missing)}. "
                "Set them in the environment or a .env file."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
