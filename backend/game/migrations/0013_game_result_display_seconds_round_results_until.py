from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0012_round_consensus_vote_counts'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='result_display_seconds',
            field=models.PositiveIntegerField(
                default=12,
                help_text='How long round results remain visible, in seconds.',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(60),
                ],
            ),
        ),
        migrations.AddField(
            model_name='round',
            name='results_until',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]