from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),  # Substitua pelo nome da última migração
    ]

    operations = [
        migrations.AddField(
            model_name='movimentacaoestoque',
            name='fazenda_origem',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movimentacoes_origem',
                to='core.fazenda',
                verbose_name='Fazenda de Origem'
            ),
        ),
    ]
