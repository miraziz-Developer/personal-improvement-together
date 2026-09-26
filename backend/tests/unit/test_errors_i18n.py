"""Every message a user can see has a Russian translation — checked against the source code, so
a new error written in Uzbek cannot slip through untranslated."""

import ast
from pathlib import Path

from pit.shared.application.errors_i18n import translate_error

SOURCE = Path(__file__).resolve().parents[2] / "src" / "pit"
RAISERS = {
    "DomainError",
    "InvariantViolation",
    "InvalidStateTransition",
    "NotFound",
    "PermissionDenied",
    "HTTPException",
    "require",
}
SKIP = ("_ru.py", "texts.py", "messages.py", "errors_i18n.py")


def user_facing_messages() -> list[str]:
    """Messages passed to the exceptions users see; f-strings get sample values."""
    found: set[str] = set()
    for path in SOURCE.rglob("*.py"):
        if path.name.endswith(SKIP):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in RAISERS:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if any(ch.isalpha() for ch in arg.value) and " " in arg.value:
                        found.add(arg.value)
                elif isinstance(arg, ast.JoinedStr):
                    found.add(
                        "".join(
                            str(v.value) if isinstance(v, ast.Constant) else "7" for v in arg.values
                        )
                    )
    return sorted(found)


def test_every_user_facing_error_speaks_russian() -> None:
    missing = [m for m in user_facing_messages() if translate_error(m, "ru") == m]
    assert not missing, "No Russian for:\n" + "\n".join(missing)


def test_values_and_weekdays_are_carried_over() -> None:
    assert translate_error("Garov 10 000 so'm dan 2 000 000 so'm gacha bo'lishi kerak", "ru") == (
        "Ставка должна быть от 10 000 so'm до 2 000 000 so'm"
    )
    assert translate_error("Dushanba: kamida bitta majburiy vazifa bo'lsin", "ru-RU").startswith(
        "Понедельник:"
    )


def test_uzbek_and_unknown_languages_keep_the_original() -> None:
    assert translate_error("Challenge topilmadi", "uz") == "Challenge topilmadi"
    assert translate_error("Challenge topilmadi", "en") == "Challenge topilmadi"
    assert translate_error("Butunlay yangi xabar", "ru") == "Butunlay yangi xabar"
