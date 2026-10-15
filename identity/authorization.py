from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from .models import Role

P = ParamSpec("P")
R = TypeVar("R", bound=HttpResponse)


def roles_required(*allowed_roles: Role.Code | str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Require an authenticated account with one explicit role on the server."""
    allowed_codes = {str(r) for r in allowed_roles}

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> R:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            user_role = getattr(request.user, "role", None)
            if not user_role or user_role.code not in allowed_codes:
                raise PermissionDenied("No tiene permiso para esta operación.")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
