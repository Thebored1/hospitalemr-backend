from django.db import models
from django.conf import settings

class CustomRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class RolePageRestriction(models.Model):
    role = models.ForeignKey(CustomRole, on_delete=models.CASCADE, related_name='page_restrictions')
    url_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('role', 'url_name')

    def __str__(self):
        return f"{self.role.name} restricted from {self.url_name}"

class UserPageRestriction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='page_restrictions')
    url_name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'url_name')

    def __str__(self):
        return f"{self.user.username} restricted from {self.url_name}"

class UserRoleAssignment(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='custom_role_assignment')
    role = models.ForeignKey(CustomRole, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} -> {self.role.name}"
