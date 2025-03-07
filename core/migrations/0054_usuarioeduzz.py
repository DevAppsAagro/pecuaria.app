# Generated by Django 5.0 on 2025-02-19 01:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0053_alter_usersubscription_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UsuarioEduzz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eduzz_id', models.CharField(blank=True, max_length=100, null=True)),
                ('subscription_id', models.CharField(blank=True, max_length=100, null=True)),
                ('plano_id', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True)),
                ('data_assinatura', models.DateTimeField(blank=True, null=True)),
                ('data_expiracao', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Usuário Eduzz',
                'verbose_name_plural': 'Usuários Eduzz',
            },
        ),
    ]
