from functools import wraps

from flask import abort
from flask_login import current_user, login_required

ROLES = {"admin": "Administrador", "manager": "Gerente", "warehouse": "Almacén", "cashier": "Caja"}
PERMISSIONS = {
    "admin": {
        "dashboard",
        "catalog.read",
        "catalog.write",
        "inventory.read",
        "inventory.write",
        "inventory.reverse",
        "inventory.waste",
        "inventory.adjust",
        "recipes.read",
        "recipes.write",
        "sales.read",
        "sales.write",
        "sales.cancel",
        "reports",
        "imports",
        "users",
        "settings",
        "audit",
    },
    "manager": {
        "dashboard",
        "catalog.read",
        "catalog.write",
        "inventory.read",
        "inventory.write",
        "inventory.reverse",
        "inventory.waste",
        "inventory.adjust",
        "recipes.read",
        "recipes.write",
        "sales.read",
        "sales.write",
        "sales.cancel",
        "reports",
        "imports",
        "audit",
    },
    "warehouse": {
        "dashboard",
        "catalog.read",
        "catalog.write",
        "inventory.read",
        "inventory.write",
    },
    "cashier": {"dashboard", "sales.read", "sales.write"},
}


def can(permission):
    return (
        current_user.is_authenticated
        and current_user.active
        and permission in PERMISSIONS.get(current_user.role, set())
    )


def permission_required(permission):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if not can(permission):
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator
