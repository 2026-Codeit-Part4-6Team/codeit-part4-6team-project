import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import PublishRequest, PublishResponse
from backend.services.generation_service import (
    ApprovedImageInvalid,
    ApprovedImageTooLarge,
    PublishedProposalConflict,
    PublishNotFound,
    PublishPersistenceError,
    PublishProposalInvalid,
    PublishStateConflict,
    PublishTypeConflict,
    publish_generation,
)

router = APIRouter(tags=["generations"])


@router.post(
    "/generations/{generation_id}/publish",
    response_model=PublishResponse,
)
def publish(
    generation_id: int,
    body: PublishRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PublishResponse:
    """소유한 Basic 생성 결과의 한 제안을 게시 승인합니다."""
    try:
        return asyncio.run(
            publish_generation(
                db,
                user,
                generation_id,
                body,
                max_image_bytes=settings.max_approved_image_bytes,
            )
        )
    except PublishNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason": "generation_not_found"},
        ) from error
    except PublishStateConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "publish_state_conflict"},
        ) from error
    except PublishTypeConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "publish_type_conflict"},
        ) from error
    except PublishedProposalConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "published_proposal_conflict"},
        ) from error
    except PublishProposalInvalid as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"reason": "invalid_proposal"},
        ) from error
    except ApprovedImageInvalid as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"reason": "invalid_approved_image"},
        ) from error
    except ApprovedImageTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={"reason": "approved_image_too_large"},
        ) from error
    except PublishPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"reason": "publish_persistence_error"},
        ) from error
