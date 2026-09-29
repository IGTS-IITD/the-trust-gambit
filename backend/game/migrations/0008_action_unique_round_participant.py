from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0007_round_duration_seconds_round_starts_at'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='action',
            unique_together={('round', 'participant')},
        ),
    ]
