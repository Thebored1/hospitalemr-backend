from django import template
from portal.models import UserRoleAssignment, RolePageRestriction, UserPageRestriction

register = template.Library()

@register.simple_tag
def has_portal_permission(user, url_name):
    if user.is_superuser:
        return True
        
    role_assignment = UserRoleAssignment.objects.filter(user=user).first()
    if role_assignment:
        if RolePageRestriction.objects.filter(role=role_assignment.role, url_name=url_name).exists():
            return False
    else:
        if UserPageRestriction.objects.filter(user=user, url_name=url_name).exists():
            return False
            
    return True
