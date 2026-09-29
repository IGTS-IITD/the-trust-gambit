from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0008_action_unique_round_participant'),
        ('game', '0008_remove_game_is_active_and_more'),
        ('game', '0009_remove_game_safety_buffer'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='consensus_mode',
            field=models.CharField(
                choices=[('MAJORITY', 'Majority'), ('MINORITY', 'Minority')],
                default='MAJORITY',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='round',
            name='question_type',
            field=models.CharField(
                choices=[('STANDARD', 'Standard'), ('CONSENSUS', 'Consensus')],
                default='STANDARD',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='round',
            name='resolved_answer',
            field=models.CharField(blank=True, editable=False, max_length=255, null=True),
        ),
    ]
