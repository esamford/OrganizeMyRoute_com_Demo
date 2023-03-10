# Generated by Django 4.0.6 on 2022-09-11 00:25

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('read', models.BooleanField(default=False)),
                ('subject', models.TextField(max_length=200)),
                ('reason', models.CharField(choices=[('Requesting a feature', 'Requesting a feature'), ('Reporting an error', 'Reporting an error'), ('Other', 'Other')], max_length=50)),
                ('message', models.TextField(max_length=3000)),
            ],
        ),
    ]
