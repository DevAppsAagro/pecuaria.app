# Generated by Django 5.0 on 2024-12-13 01:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_contabancaria_optional_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Contato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('tipo', models.CharField(choices=[('FO', 'Fornecedor'), ('FU', 'Funcionário'), ('CO', 'Comprador'), ('SO', 'Sócio')], max_length=2, verbose_name='Tipo')),
                ('telefone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Telefone')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='E-mail')),
                ('cidade', models.CharField(max_length=100, verbose_name='Cidade')),
                ('uf', models.CharField(max_length=2, verbose_name='UF')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Contato',
                'verbose_name_plural': 'Contatos',
                'ordering': ['nome'],
            },
        ),
    ]
