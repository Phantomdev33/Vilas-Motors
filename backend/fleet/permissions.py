from rest_framework.permissions import BasePermission

MATRIX = {
    'equipment': {'admin': 'CRUD', 'planner': 'CRU', 'helper': 'CR', 'chief': 'R'},
    'reading': {'admin': 'CRUD', 'planner': 'CRU', 'helper': 'CR', 'chief': 'R'},
    'maintenance': {'admin': 'CRUD', 'planner': 'CRUD', 'helper': 'CR', 'chief': 'R'},
    'supply': {'admin': 'CRUD', 'planner': 'CRU', 'helper': 'R', 'chief': 'R'},
    'alert': {'admin': 'CRUD', 'planner': 'R', 'helper': 'R', 'chief': 'R'},
    'user': {'admin': 'CRUD', 'planner': '', 'helper': '', 'chief': 'R'},
    'audit': {'admin': 'R'},
}

class RolePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated: return False
        operation = {'GET': 'R', 'HEAD': 'R', 'OPTIONS': 'R', 'POST': 'C', 'PUT': 'U', 'PATCH': 'U', 'DELETE': 'D'}.get(request.method, '')
        return operation in MATRIX.get(view.permission_module, {}).get(request.user.role, '')
