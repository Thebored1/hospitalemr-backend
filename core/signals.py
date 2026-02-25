from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import AgentAssignment, Area


@receiver(post_delete, sender=AgentAssignment)
def clear_area_agent_on_assignment_delete(sender, instance, **kwargs):
    """
    When an AgentAssignment is deleted, check if the area still has another active assignment.
    If not, clear the Area.agent pointer so the mobile app no longer shows those doctors.
    """
    area = instance.area
    # Check if there's still another assignment for this area
    still_assigned = AgentAssignment.objects.filter(area=area).exists()
    if not still_assigned:
        area.agent = None
        area.save(update_fields=['agent'])


@receiver(post_save, sender=AgentAssignment)
def set_area_agent_on_assignment_create(sender, instance, created, **kwargs):
    """
    When a new AgentAssignment is created, update the Area.agent pointer.
    """
    if created:
        area = instance.area
        area.agent = instance.agent
        area.save(update_fields=['agent'])
