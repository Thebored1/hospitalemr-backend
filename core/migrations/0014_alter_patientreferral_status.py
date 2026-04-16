from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_user_hardware_id_user_hardware_id_authorized_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientreferral',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Admitted', 'Admitted'), ('Dismissed', 'Dismissed')], default='Pending', max_length=20),
        ),
    ]
