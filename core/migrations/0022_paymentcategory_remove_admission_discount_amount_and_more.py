# Custom migration: Create PaymentCategory, seed defaults, map existing data
# Handles SQLite limitations with unique_together by removing constraint first

import django.db.models.deletion
from django.db import migrations, models


DEFAULT_CATEGORIES = [
    ('CASH', 'Cash'),
    ('INSURANCE', 'Insurance'),
    ('AYUSHMAN', 'Ayushman Bharat'),
]


def seed_categories_and_map_data(apps, schema_editor):
    """Create default payment categories and map existing string data to FK."""
    PaymentCategory = apps.get_model('core', 'PaymentCategory')
    Admission = apps.get_model('core', 'Admission')
    DoctorCommissionProfile = apps.get_model('core', 'DoctorCommissionProfile')

    # Create default categories
    category_map = {}
    for code, name in DEFAULT_CATEGORIES:
        cat, _ = PaymentCategory.objects.get_or_create(code=code, defaults={'name': name})
        category_map[code] = cat

    # Map Admission rows
    for admission in Admission.objects.all():
        old_val = admission.payment_category_old
        if old_val and old_val in category_map:
            admission.payment_category_new = category_map[old_val]
            admission.save(update_fields=['payment_category_new'])

    # Map DoctorCommissionProfile rows  
    for profile in DoctorCommissionProfile.objects.all():
        old_val = profile.payment_category_old
        if old_val and old_val in category_map:
            profile.payment_category_new = category_map[old_val]
            profile.save(update_fields=['payment_category_new'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_remove_admission_referral_amount_and_more'),
    ]

    operations = [
        # 1. Create PaymentCategory model
        migrations.CreateModel(
            name='PaymentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('code', models.CharField(help_text='Short code e.g. CASH, INSURANCE', max_length=50, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Payment Categories',
                'ordering': ['name'],
            },
        ),

        # 2. Remove discount_amount from Admission (was removed from model)
        migrations.RemoveField(
            model_name='admission',
            name='discount_amount',
        ),

        # 3. Drop unique_together on DoctorCommissionProfile BEFORE renaming
        migrations.AlterUniqueTogether(
            name='doctorcommissionprofile',
            unique_together=set(),
        ),

        # 4. Rename old CharField columns to _old
        migrations.RenameField(
            model_name='admission',
            old_name='payment_category',
            new_name='payment_category_old',
        ),
        migrations.RenameField(
            model_name='doctorcommissionprofile',
            old_name='payment_category',
            new_name='payment_category_old',
        ),

        # 5. Add new FK columns (nullable)
        migrations.AddField(
            model_name='admission',
            name='payment_category_new',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='admissions_new',
                to='core.paymentcategory',
            ),
        ),
        migrations.AddField(
            model_name='doctorcommissionprofile',
            name='payment_category_new',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='commission_profiles_new',
                to='core.paymentcategory',
            ),
        ),

        # 6. Seed categories and map data
        migrations.RunPython(seed_categories_and_map_data, reverse_noop),

        # 7. Drop old string columns
        migrations.RemoveField(
            model_name='admission',
            name='payment_category_old',
        ),
        migrations.RemoveField(
            model_name='doctorcommissionprofile',
            name='payment_category_old',
        ),

        # 8. Rename _new columns to final name
        migrations.RenameField(
            model_name='admission',
            old_name='payment_category_new',
            new_name='payment_category',
        ),
        migrations.RenameField(
            model_name='doctorcommissionprofile',
            old_name='payment_category_new',
            new_name='payment_category',
        ),

        # 9. Set final field properties and constraints
        migrations.AlterField(
            model_name='admission',
            name='payment_category',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='admissions',
                to='core.paymentcategory',
            ),
        ),
        migrations.AlterField(
            model_name='doctorcommissionprofile',
            name='payment_category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='commission_profiles',
                to='core.paymentcategory',
            ),
        ),

        # 10. Restore unique_together with the new FK
        migrations.AlterUniqueTogether(
            name='doctorcommissionprofile',
            unique_together={('doctor', 'payment_category')},
        ),
    ]
