import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("modules", "0002_retentionpolicy"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="record_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("merged", "Merged"),
                    ("archived", "Archived"),
                ],
                default="active",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="merged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contact",
            name="merged_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contact_merges",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="merged_into",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="merged_contacts",
                to="modules.contact",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["organization", "record_status"],
                name="modules_con_organiz_97236f_idx",
            ),
        ),
    ]
