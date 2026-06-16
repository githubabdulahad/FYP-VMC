from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadrecord',
            name='file_url',
            field=models.URLField(blank=True, default='', max_length=1000),
        ),
    ]