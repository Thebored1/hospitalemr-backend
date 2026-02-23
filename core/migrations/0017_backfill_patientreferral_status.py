from django.db import migrations


def backfill_patientreferral_status(apps, schema_editor):
    PatientReferral = apps.get_model('core', 'PatientReferral')
    PatientReferral.objects.filter(status__isnull=True).update(status='Pending')
    PatientReferral.objects.filter(status='').update(status='Pending')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_remove_user_hardware_id_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_patientreferral_status, migrations.RunPython.noop),
    ]
