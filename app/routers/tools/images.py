# Plik: app/routers/tools/images.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pathlib import Path
import shutil
import re
import base64
import uuid
from PIL import Image
from io import BytesIO
from datetime import datetime

from ...db import get_session
from ...models import Tool as ToolModel
from ...dependencies import require_role
from ...config import settings
from ...exceptions import ResourceNotFound, OperationForbidden
from .schemas import ToolOut, Base64ImagePayload, LocalImagePayload

router = APIRouter()


@router.post(
    "/{tool_id}/upload-base64-image",
    response_model=ToolOut,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def upload_base64_image(
    tool_id: int, payload: Base64ImagePayload, session: Session = Depends(get_session)
):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)
    try:
        header, encoded_data = payload.image_data.split(",", 1)
        match = re.search(r"data:image/(?P<ext>jpeg|png|gif)", header)
        if not match:
            raise OperationForbidden(
                reason="Invalid image format. Only jpeg, png, gif are supported."
            )
        file_extension = "." + match.group("ext")
        image_bytes = base64.b64decode(encoded_data)
    except (ValueError, TypeError) as e:
        raise OperationForbidden(reason=f"Invalid Base64 data: {e}")
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    image_dir = Path("static/images")
    icon_dir = Path("static/icons")
    image_dir.mkdir(exist_ok=True)
    icon_dir.mkdir(exist_ok=True)

    image_path = image_dir / unique_filename
    icon_path = icon_dir / unique_filename

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.save(image_path)
            img.thumbnail((100, 100))
            img.save(icon_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and save image: {e}",
        )

    tool.image_url = f"/static/images/{unique_filename}"
    tool.icons_url = f"/static/icons/{unique_filename}"
    tool.updated_at = datetime.now()
    session.add(tool)
    session.commit()
    session.refresh(tool)
    return tool


@router.post(
    "/{tool_id}/assign-local-image",
    response_model=ToolOut,
    dependencies=[Depends(require_role("admin", "moderator"))],
)
def assign_local_image(
    tool_id: int, payload: LocalImagePayload, session: Session = Depends(get_session)
):
    tool = session.get(ToolModel, tool_id)
    if not tool:
        raise ResourceNotFound(name="Tool", resource_id=tool_id)
    source_path = Path(payload.local_path)
    if not source_path.is_file():
        raise ResourceNotFound(name="Source file", resource_id=str(source_path))
    allowed_path = Path(settings.ALLOWED_LOCAL_PATH).resolve()
    if not source_path.resolve().is_relative_to(allowed_path):
        raise OperationForbidden(reason="File path is outside the allowed directory.")
    upload_dir = Path("static/images")
    icon_dir = Path("static/icons")
    upload_dir.mkdir(exist_ok=True)
    icon_dir.mkdir(exist_ok=True)
    file_extension = source_path.suffix
    new_filename = f"{uuid.uuid4()}{file_extension}"
    destination_path = upload_dir / new_filename
    icon_path = icon_dir / new_filename
    try:
        with Image.open(source_path) as img:
            img.save(destination_path)
            img.thumbnail((100, 100))
            img.save(icon_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and save image: {e}",
        )
    tool.image_url = f"/static/images/{new_filename}"
    tool.icons_url = f"/static/icons/{new_filename}"
    tool.updated_at = datetime.now()
    session.add(tool)
    session.commit()
    session.refresh(tool)
    return tool
