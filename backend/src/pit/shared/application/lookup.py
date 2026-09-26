from pit.shared.domain.errors import NotFound


def require[T](value: T | None, message: str) -> T:
    if value is None:
        raise NotFound(message)
    return value
