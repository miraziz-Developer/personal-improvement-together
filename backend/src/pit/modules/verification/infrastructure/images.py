"""Proof photos: validate, shrink, strip metadata (EXIF/GPS never leaves the server) and hash."""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from pit.shared.domain.errors import DomainError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SIDE = 1600
Image.MAX_IMAGE_PIXELS = 40_000_000  # refuse decompression bombs


def prepare_proof_image(data: bytes) -> tuple[bytes, str]:
    """Returns (clean JPEG bytes, perceptual hash)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise DomainError("Rasm 10 MB dan oshmasligi kerak")
    try:
        opened = Image.open(io.BytesIO(data))
        opened.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise DomainError("Faqat rasm fayllari qabul qilinadi (JPG, PNG, HEIC emas)") from error
    image = ImageOps.exif_transpose(opened).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    output = io.BytesIO()
    image.save(output, "JPEG", quality=85, optimize=True)  # re-encoding drops all metadata
    return output.getvalue(), dhash(image)


def dhash(image: Image.Image, size: int = 8) -> str:
    """Difference hash: survives resizing and re-compression, so a re-uploaded photo matches."""
    gray = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = gray.tobytes()  # one byte per pixel in mode 'L'
    bits = 0
    for row in range(size):
        for col in range(size):
            left, right = pixels[row * (size + 1) + col], pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | int(left > right)
    return f"{bits:0{size * size // 4}x}"
