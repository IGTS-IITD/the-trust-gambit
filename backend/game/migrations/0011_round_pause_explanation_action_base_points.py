from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0010_round_consensus_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='answer_explanation',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='round',
            name='is_paused',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='round',
            name='paused_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='round',
            name='paused_remaining_seconds',
            field=models.FloatField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='action',
            name='base_points_awarded',
            field=models.FloatField(default=0),
        ),
    ]