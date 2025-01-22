from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0028_add_user_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovimentacaoNaoOperacional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(verbose_name='Data')),
                ('data_vencimento', models.DateField(verbose_name='Data de Vencimento')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='Data de Pagamento/Recebimento')),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('saida', 'Saída')], max_length=10, verbose_name='Tipo')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Valor')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Data de Atualização')),
                ('conta_bancaria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.contabancaria', verbose_name='Conta Bancária')),
                ('fazenda', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.fazenda')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Movimentação Não Operacional',
                'verbose_name_plural': 'Movimentações Não Operacionais',
                'ordering': ['-data', '-data_cadastro'],
            },
        ),
    ]
