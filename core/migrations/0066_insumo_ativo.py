# Generated by Django 5.0 on 2025-03-27 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0065_despesa_boleto'),
    ]

    operations = [
        migrations.AddField(
            model_name='insumo',
            name='ativo',
            field=models.BooleanField(default=True, verbose_name='Ativo'),
        ),
    ]
