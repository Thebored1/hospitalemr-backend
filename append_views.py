
# ============ Permission Management ============
from .models import CustomRole, RolePageRestriction, UserPageRestriction, UserRoleAssignment
from django.http import JsonResponse

def get_all_portal_pages():
    from portal.urls import urlpatterns as portal_urlpatterns
    pages = []
    excluded_names = [
        'permission_list', 'permission_update', 'create_custom_role', 
        'backup_dashboard', 'backup_export', 'backup_import'
    ]
    for pattern in portal_urlpatterns:
        if hasattr(pattern, 'name') and pattern.name:
            if not pattern.name.startswith('api_') and pattern.name not in excluded_names:
                pages.append({
                    'name': pattern.name,
                    'title': pattern.name.replace('_', ' ').title()
                })
    return pages

class UserPermissionListView(PortalMixin, ListView):
    """List all staff users to manage their permissions."""
    model = User
    template_name = 'portal/permissions/list.html'
    context_object_name = 'users'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can manage permissions.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.filter(is_staff=True).order_by('username')

class UserPermissionUpdateView(PortalMixin, DetailView):
    """Update permissions for a specific user."""
    model = User
    template_name = 'portal/permissions/update.html'
    context_object_name = 'user_obj'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Only superusers can manage permissions.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        context['pages'] = get_all_portal_pages()
        context['roles'] = CustomRole.objects.all()
        
        # Current role assignment
        role_assignment = UserRoleAssignment.objects.filter(user=user).first()
        context['current_role'] = role_assignment.role if role_assignment else None
        
        if role_assignment:
            restricted = RolePageRestriction.objects.filter(role=role_assignment.role).values_list('url_name', flat=True)
        else:
            restricted = UserPageRestriction.objects.filter(user=user).values_list('url_name', flat=True)
            
        context['restricted_pages'] = set(restricted)
        return context

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        role_id = request.POST.get('role')
        
        # Clear existing
        UserRoleAssignment.objects.filter(user=user).delete()
        
        if role_id and role_id != 'none':
            from django.shortcuts import get_object_or_404
            role = get_object_or_404(CustomRole, pk=role_id)
            UserRoleAssignment.objects.create(user=user, role=role)
            # If a role is assigned, we ignore individual checkbox submissions
        else:
            # Individual permissions
            UserPageRestriction.objects.filter(user=user).delete()
            all_pages = [p['name'] for p in get_all_portal_pages()]
            # Allowed pages are the checked ones
            allowed_pages = request.POST.getlist('pages')
            
            # Restricted pages are the ones NOT checked
            for page in all_pages:
                if page not in allowed_pages:
                    UserPageRestriction.objects.create(user=user, url_name=page)
                    
        messages.success(request, f'Permissions updated for {user.username}.')
        return redirect('portal:permission_update', pk=user.pk)

@staff_member_required
def create_custom_role(request):
    """AJAX endpoint to create a new CustomRole and its restrictions."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        name = request.POST.get('name')
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
            
        if CustomRole.objects.filter(name=name).exists():
            return JsonResponse({'error': 'Role with this name already exists'}, status=400)
            
        role = CustomRole.objects.create(name=name)
        
        all_pages = [p['name'] for p in get_all_portal_pages()]
        allowed_pages = request.POST.getlist('pages[]')
        
        for page in all_pages:
            if page not in allowed_pages:
                RolePageRestriction.objects.create(role=role, url_name=page)
                
        return JsonResponse({'success': True, 'role_id': role.id, 'role_name': role.name})
    return JsonResponse({'error': 'Invalid request'}, status=400)
