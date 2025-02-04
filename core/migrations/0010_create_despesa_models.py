# Generated by Django 5.0 on 2024-12-13 04:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_fix_contato_table'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Despesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_nf', models.CharField(max_length=50, verbose_name='Número NF')),
                ('data_emissao', models.DateField(verbose_name='Data de Emissão')),
                ('forma_pagamento', models.CharField(choices=[('AV', 'À Vista'), ('PA', 'Parcelado')], max_length=2, verbose_name='Forma de Pagamento')),
                ('arquivo', models.FileField(blank=True, null=True, upload_to='despesas/', verbose_name='Arquivo')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('contato', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.contato')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Despesa',
                'verbose_name_plural': 'Despesas',
                'ordering': ['-data_emissao'],
            },
        ),
        migrations.CreateModel(
            name='ItemDespesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor Unitário')),
                ('quantidade', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='Quantidade')),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor Total')),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.categoriacusto')),
                ('despesa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='core.despesa')),
                ('subcategoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.subcategoriacusto')),
            ],
            options={
                'verbose_name': 'Item da Despesa',
                'verbose_name_plural': 'Itens da Despesa',
            },
        ),
        migrations.CreateModel(
            name='AlocacaoDespesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('benfeitoria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.benfeitoria')),
                ('fazenda', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.fazenda')),
                ('lote', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.lote')),
                ('maquina', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.maquina')),
                ('pasto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.pasto')),
                ('item_despesa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alocacoes', to='core.itemdespesa')),
            ],
            options={
                'verbose_name': 'Alocação de Despesa',
                'verbose_name_plural': 'Alocações de Despesas',
            },
        ),
        migrations.CreateModel(
            name='RateioDespesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor Rateado')),
                ('data_rateio', models.DateField(auto_now_add=True)),
                ('alocacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rateios', to='core.alocacaodespesa')),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.animal')),
            ],
            options={
                'verbose_name': 'Rateio de Despesa',
                'verbose_name_plural': 'Rateios de Despesas',
            },
        ),
    ]
