from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0011_round_pause_explanation_action_base_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='consensus_vote_counts',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]