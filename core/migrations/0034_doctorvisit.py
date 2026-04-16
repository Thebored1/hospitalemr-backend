from django.db import migrations, models
import django.db.models.deletion


def backfill_doctor_visits(apps, schema_editor):
    DoctorReferral = apps.get_model('core', 'DoctorReferral')
    DoctorVisit = apps.get_model('core', 'DoctorVisit')

    referrals = DoctorReferral.objects.exclude(trip__isnull=True).iterator()
    for referral in referrals:
        visit, created = DoctorVisit.objects.get_or_create(
            doctor_id=referral.id,
            trip_id=referral.trip_id,
            defaults={
                'remarks': referral.remarks,
                'additional_details': referral.additional_details,
                'status': referral.status or 'Referred',
                'visit_image': referral.visit_image,
                'visit_lat': referral.visit_lat,
                'visit_long': referral.visit_long,
            },
        )
        if created:
            DoctorVisit.objects.filter(pk=visit.pk).update(created_at=referral.created_at)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_alter_address_pincode'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoctorVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remarks', models.TextField(blank=True, null=True)),
                ('additional_details', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Assigned', 'Assigned'), ('Referred', 'Referred'), ('Internal', 'Internal')], default='Referred', max_length=50)),
                ('visit_image', models.ImageField(blank=True, null=True, upload_to='doctor_visits/')),
                ('visit_lat', models.DecimalField(blank=True, decimal_places=15, max_digits=20, null=True)),
                ('visit_long', models.DecimalField(blank=True, decimal_places=15, max_digits=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visits', to='core.doctorreferral')),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_visits', to='core.trip')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('doctor', 'trip')},
            },
        ),
        migrations.RunPython(backfill_doctor_visits, migrations.RunPython.noop),
    ]
