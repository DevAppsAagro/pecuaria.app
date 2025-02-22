# Generated by Django 5.0 on 2025-02-17 04:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_clientelegado_ativo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eduzztransaction',
            options={'ordering': ['-data_pagamento'], 'verbose_name': 'Transação Eduzz', 'verbose_name_plural': 'Transações Eduzz'},
        ),
        migrations.AddField(
            model_name='eduzztransaction',
            name='is_legado',
            field=models.BooleanField(default=False, help_text='Indica se é um cliente que migrou da planilha'),
        ),
    ]
