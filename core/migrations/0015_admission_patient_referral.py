from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_patientreferral_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='admission',
            name='patient_referral',
            field=models.ForeignKey(blank=True, help_text='Linked patient referral for auto status updates', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admissions', to='core.patientreferral'),
        ),
    ]
