from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

def forward_func(apps, schema_editor):
    # Obter o primeiro usuário do sistema
    User = apps.get_model('auth', 'User')
    first_user = User.objects.first()
    
    if first_user:
        # Atualizar cada modelo com o primeiro usuário
        Raca = apps.get_model('core', 'Raca')
        CategoriaAnimal = apps.get_model('core', 'CategoriaAnimal')
        VariedadeCapim = apps.get_model('core', 'VariedadeCapim')
        MotivoMorte = apps.get_model('core', 'MotivoMorte')
        CategoriaCusto = apps.get_model('core', 'CategoriaCusto')
        SubcategoriaCusto = apps.get_model('core', 'SubcategoriaCusto')
        
        Raca.objects.filter(usuario__isnull=True).update(usuario=first_user)
        CategoriaAnimal.objects.filter(usuario__isnull=True).update(usuario=first_user)
        VariedadeCapim.objects.filter(usuario__isnull=True).update(usuario=first_user)
        MotivoMorte.objects.filter(usuario__isnull=True).update(usuario=first_user)
        CategoriaCusto.objects.filter(usuario__isnull=True).update(usuario=first_user)
        SubcategoriaCusto.objects.filter(usuario__isnull=True).update(usuario=first_user)

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0027_update_finalidade_lote_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='raca',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='categoriaanimal',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='variedadecapim',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='motivomorte',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='categoriacusto',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='subcategoriacusto',
            name='usuario',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(forward_func),
        migrations.AlterField(
            model_name='raca',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='categoriaanimal',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='variedadecapim',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='motivomorte',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='categoriacusto',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='subcategoriacusto',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='raca',
            unique_together={('nome', 'usuario')},
        ),
        migrations.AlterUniqueTogether(
            name='categoriaanimal',
            unique_together={('nome', 'sexo', 'usuario')},
        ),
        migrations.AlterUniqueTogether(
            name='variedadecapim',
            unique_together={('nome', 'usuario')},
        ),
        migrations.AlterUniqueTogether(
            name='motivomorte',
            unique_together={('nome', 'usuario')},
        ),
        migrations.AlterUniqueTogether(
            name='categoriacusto',
            unique_together={('nome', 'usuario')},
        ),
        migrations.AlterUniqueTogether(
            name='subcategoriacusto',
            unique_together={('categoria', 'nome', 'usuario')},
        ),
    ]
