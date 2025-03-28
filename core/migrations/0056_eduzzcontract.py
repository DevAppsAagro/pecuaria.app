# Generated by Django 5.0 on 2025-02-24 19:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_clienteplanilha'),
    ]

    operations = [
        migrations.CreateModel(
            name='EduzzContract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_id', models.CharField(max_length=100, unique=True)),
                ('status', models.CharField(max_length=50)),
                ('customer_email', models.EmailField(max_length=254)),
                ('customer_name', models.CharField(max_length=255)),
                ('plan_id', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Contrato Eduzz',
                'verbose_name_plural': 'Contratos Eduzz',
            },
        ),
    ]
