# Generated for topic title color support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0011_topic_duration_seconds_topic_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='title_color',
            field=models.CharField(blank=True, max_length=9, null=True),
        ),
    ]
