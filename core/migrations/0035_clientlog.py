from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_doctorvisit'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('DEBUG', 'Debug'), ('INFO', 'Info'), ('WARN', 'Warn'), ('ERROR', 'Error')], default='INFO', max_length=10)),
                ('message', models.TextField()),
                ('logger', models.CharField(blank=True, max_length=100, null=True)),
                ('context', models.JSONField(blank=True, default=dict)),
                ('device_id', models.CharField(blank=True, max_length=64, null=True)),
                ('app_version', models.CharField(blank=True, max_length=32, null=True)),
                ('platform', models.CharField(blank=True, max_length=32, null=True)),
                ('build_mode', models.CharField(blank=True, max_length=16, null=True)),
                ('client_time', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.CharField(blank=True, max_length=45, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='client_logs', to='core.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
