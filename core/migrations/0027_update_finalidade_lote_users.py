from django.db import migrations

def atribuir_usuario_padrao(apps, schema_editor):
    FinalidadeLote = apps.get_model('core', 'FinalidadeLote')
    User = apps.get_model('auth', 'User')
    
    # Pega o primeiro usuário do sistema
    primeiro_usuario = User.objects.first()
    if primeiro_usuario:
        # Atualiza todas as finalidades sem usuário
        FinalidadeLote.objects.filter(usuario__isnull=True).update(usuario=primeiro_usuario)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_add_usuario_to_finalidade_lote'),
    ]

    operations = [
        migrations.RunPython(atribuir_usuario_padrao),
    ]
