from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from pit.api.deps import ContainerDep
from pit.modules.verification.infrastructure.storage import LocalFileStorage

router = APIRouter(tags=["media"])


@router.get("/media/{key:path}", include_in_schema=False)
async def media(key: str, exp: int, sig: str, container: ContainerDep) -> FileResponse:
    """Serves locally stored proof photos behind a signed, expiring link (like S3 presigning)."""
    storage = container.storage
    if not isinstance(storage, LocalFileStorage) or not storage.verify(key, exp, sig):
        raise HTTPException(404, "Topilmadi")
    try:
        path = storage.path_for(key)
    except ValueError as error:
        raise HTTPException(404, "Topilmadi") from error
    if not path.is_file():
        raise HTTPException(404, "Topilmadi")
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=600"}
    )
