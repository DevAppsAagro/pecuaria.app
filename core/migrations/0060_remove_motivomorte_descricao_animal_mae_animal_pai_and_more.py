# Generated by Django 5.0 on 2025-03-12 19:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_auto_20250312_1527'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='motivomorte',
            name='descricao',
        ),
        migrations.AddField(
            model_name='animal',
            name='mae',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='filhos', to='core.animal', verbose_name='Mãe'),
        ),
        migrations.AddField(
            model_name='animal',
            name='pai',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='filhos_pai', to='core.animal', verbose_name='Pai'),
        ),
        migrations.AddField(
            model_name='animal',
            name='tipo_origem_paterna',
            field=models.CharField(blank=True, choices=[('ANIMAL', 'Animal'), ('SEMEN', 'Sêmen')], max_length=10, null=True, verbose_name='Tipo Origem Paterna'),
        ),
    ]
