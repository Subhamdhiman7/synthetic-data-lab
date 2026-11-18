"""FastAPI dependencies shared by backend routes."""

import os
from pathlib import Path

from fastapi import Request

from backend.services.dataset_service import DatasetService
from backend.storage.history import LocalStorage


def get_service(request: Request) -> DatasetService:
    """Return the application service, initialized lazily for safe imports."""
    service = getattr(request.app.state, "dataset_service", None)
    if service is None:
        storage_root = Path(
            os.getenv("SYNTHETIC_DATA_LAB_STORAGE", "backend_data")
        )
        service = DatasetService(LocalStorage(storage_root))
        request.app.state.dataset_service = service
    return service
