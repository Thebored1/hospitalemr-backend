from rest_framework.permissions import BasePermission
from portal.models import UserRoleAssignment, RolePageRestriction, UserPageRestriction

class DynamicAPIPermission(BasePermission):
    """
    Checks if the user has access to this DRF API endpoint based on the dynamic permission system.
    """
    def has_permission(self, request, view):
        # We assume they are already authenticated via IsAuthenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_superuser:
            return True
            
        if not request.resolver_match:
            return True
            
        url_name = request.resolver_match.url_name
        if not url_name:
            return True
            
        # For a ViewSet, url_name is usually "basename-list" or "basename-detail"
        basename = url_name.split('-')[0]
        permission_name = f"api_{basename}"
        
        is_restricted = False
        role_assignment = UserRoleAssignment.objects.filter(user=request.user).first()
        if role_assignment:
            if RolePageRestriction.objects.filter(role=role_assignment.role, url_name=permission_name).exists():
                is_restricted = True
        else:
            if UserPageRestriction.objects.filter(user=request.user, url_name=permission_name).exists():
                is_restricted = True
                
        return not is_restricted
