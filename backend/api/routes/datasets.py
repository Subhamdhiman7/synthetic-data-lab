"""Dataset generation and artifact endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from backend.api.dependencies import get_service
from backend.schemas.requests import GenerateDatasetRequest
from backend.schemas.responses import (
    GenerationResponse,
    HistoryResponse,
    PreviewResponse,
    ReportResponse,
    GenerationMetadata,
)
from backend.services.dataset_service import DatasetService
from backend.storage.history import CorruptArtifactError, NotFoundError
from backend.schemas.analysis import AnalysisResponse


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _metadata(record: dict) -> GenerationMetadata:
    return GenerationMetadata(
        generation_id=record["generation_id"],
        plan_id=record["plan_id"],
        created_at=record["created_at"],
        dataset_name=record["dataset_name"],
        task=record["task"],
        rows=record["rows"],
        feature_count=record["feature_count"],
        files={
            "csv": True,
            "report": True,
            "plan": True,
        },
    )


@router.post("/generate", response_model=GenerationResponse, status_code=201)
def generate_dataset_endpoint(
    request: GenerateDatasetRequest,
    service: DatasetService = Depends(get_service),
) -> GenerationResponse:
    try:
        record = service.generate(request)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Saved plan is corrupted.") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Dataset generation failed")
        raise HTTPException(status_code=500, detail="Dataset generation failed.") from None
    return GenerationResponse(generation=_metadata(record))


@router.get("/history", response_model=HistoryResponse)
def history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: DatasetService = Depends(get_service),
) -> HistoryResponse:
    records, total = service.storage.list_generations(limit, offset)
    return HistoryResponse(
        items=[_metadata(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{generation_id}/preview", response_model=PreviewResponse)
def preview(
    generation_id: UUID,
    service: DatasetService = Depends(get_service),
) -> PreviewResponse:
    try:
        return PreviewResponse(**service.preview(generation_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset artifact is corrupted.") from None
    except Exception:
        logger.exception("Dataset preview failed")
        raise HTTPException(status_code=500, detail="Dataset preview is unavailable.") from None


@router.get("/{generation_id}", response_model=GenerationMetadata)
def details(
    generation_id: UUID,
    service: DatasetService = Depends(get_service),
) -> GenerationMetadata:
    try:
        return GenerationMetadata(**service.details(generation_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset artifact is corrupted.") from None


@router.get("/{generation_id}/report", response_model=ReportResponse)
def report(
    generation_id: UUID,
    service: DatasetService = Depends(get_service),
) -> ReportResponse:
    try:
        return ReportResponse(**service.report(generation_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset artifact is corrupted.") from None
    except Exception:
        logger.exception("Quality report retrieval failed")
        raise HTTPException(status_code=500, detail="Quality report is unavailable.") from None


@router.get("/{generation_id}/analysis", response_model=AnalysisResponse)
def analysis(generation_id: UUID, service: DatasetService = Depends(get_service)) -> AnalysisResponse:
    try:
        return AnalysisResponse(**service.analysis(generation_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset or saved plan is corrupted.") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Dataset analysis failed")
        raise HTTPException(status_code=500, detail="Dataset analysis is unavailable.") from None


@router.get("/{generation_id}/analysis/report", response_class=HTMLResponse)
def analysis_report(generation_id: UUID, service: DatasetService = Depends(get_service)) -> HTMLResponse:
    try:
        result, document = service.analysis_report(generation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset or saved plan is corrupted.") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Analysis report export failed")
        raise HTTPException(status_code=500, detail="Analysis report export is unavailable.") from None
    return HTMLResponse(content=document, headers={"Content-Disposition": f"attachment; filename={result['dataset_name']}_analysis.html"})


@router.get("/{generation_id}/download")
def download(
    generation_id: UUID,
    service: DatasetService = Depends(get_service),
) -> FileResponse:
    try:
        record, path = service.download_path(generation_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CorruptArtifactError:
        raise HTTPException(status_code=422, detail="Dataset artifact is corrupted.") from None
    return FileResponse(
        path,
        media_type="text/csv",
        filename=f"{record['dataset_name']}.csv",
    )
