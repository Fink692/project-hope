from django.db import migrations, models
from django.db.models.functions import Lower


def normalize_user_emails(apps, schema_editor):
    User = apps.get_model("identity", "User")
    seen = {}
    updates = []
    for user in User.objects.order_by("date_joined", "id").iterator():
        normalized = user.email.strip().lower()
        existing_id = seen.get(normalized)
        if existing_id is not None and existing_id != user.id:
            raise RuntimeError(
                "Project Hope cannot normalize user emails because two accounts "
                f"differ only by letter case: {existing_id} and {user.id}. Resolve "
                "the duplicate before applying identity.0005."
            )
        seen[normalized] = user.id
        if user.email != normalized:
            user.email = normalized
            updates.append(user)
    if updates:
        User.objects.bulk_update(updates, ["email"])


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0004_organizationinvitation"),
    ]

    operations = [
        migrations.RunPython(normalize_user_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                Lower("email"), name="unique_user_email_ci"
            ),
        ),
    ]
