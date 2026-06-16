"""
Auto-generated migration for enhanced CodingResult model and new ReviewFeedback model.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coding', '0002_create_codingresult_table'),
    ]

    operations = [
        # Add new fields to CodingResult
        migrations.AddField(
            model_name='codingresult',
            name='extracted_evidence',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='codingresult',
            name='validation_metadata',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='codingresult',
            name='review_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='codingresult',
            name='reviewed_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_coding_results',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='codingresult',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Create ReviewFeedback model
        migrations.CreateModel(
            name='ReviewFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('llm_codes', models.JSONField(default=list)),
                ('corrected_codes', models.JSONField(default=list)),
                ('feedback_type', models.CharField(
                    choices=[
                        ('missing_code', 'Missing Code Added'),
                        ('incorrect_code', 'Code Corrected'),
                        ('specificity', 'Increased Specificity'),
                        ('completeness', 'Enhanced Completeness'),
                        ('conflict_resolved', 'Conflicting Code Removed'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=50,
                )),
                ('explanation', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('coding_result', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='review_feedback',
                    to='coding.codingresult',
                )),
                ('reviewer', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='coding_feedback',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
