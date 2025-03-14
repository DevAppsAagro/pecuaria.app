# Generated by Django 5.0 on 2025-03-12 19:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_remove_motivomorte_descricao_animal_mae_animal_pai_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='animal',
            name='estacao_monta',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.estacaomonta', verbose_name='Estação de Monta'),
        ),
    ]
