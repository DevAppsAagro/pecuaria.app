-- Script SQL para limpar todas as tabelas do banco de dados
-- ATENÇÃO: Este script apagará TODOS os dados do banco. Use com cautela!

-- Desabilita restrições de chave estrangeira temporariamente
SET session_replication_role = 'replica';

-- Limpa tabelas do aplicativo core
TRUNCATE TABLE core_rateiocusto CASCADE;
TRUNCATE TABLE core_itemdespesa CASCADE;
TRUNCATE TABLE core_parceladespesa CASCADE;
TRUNCATE TABLE core_despesa CASCADE;
TRUNCATE TABLE core_movimentacaonaooperacional CASCADE;
TRUNCATE TABLE core_extratobancario CASCADE;
TRUNCATE TABLE core_contabancaria CASCADE;
TRUNCATE TABLE core_registromorte CASCADE;
TRUNCATE TABLE core_manejosanitario CASCADE;
TRUNCATE TABLE core_pesagem CASCADE;
TRUNCATE TABLE core_movimentacaoanimal CASCADE;
TRUNCATE TABLE core_animal CASCADE;
TRUNCATE TABLE core_lote CASCADE;
TRUNCATE TABLE core_finalidadelote CASCADE;
TRUNCATE TABLE core_pasto CASCADE;
TRUNCATE TABLE core_variedadecapim CASCADE;
TRUNCATE TABLE core_categoriaanimal CASCADE;
TRUNCATE TABLE core_raca CASCADE;
TRUNCATE TABLE core_benfeitoria CASCADE;
TRUNCATE TABLE core_maquina CASCADE;
TRUNCATE TABLE core_contato CASCADE;
TRUNCATE TABLE core_subcategoriacusto CASCADE;
TRUNCATE TABLE core_categoriacusto CASCADE;
TRUNCATE TABLE core_motivomorte CASCADE;
TRUNCATE TABLE core_unidademedida CASCADE;
TRUNCATE TABLE core_fazenda CASCADE;
TRUNCATE TABLE core_profile CASCADE;

-- Limpa tabelas de reprodução
TRUNCATE TABLE core_manejoreproducao CASCADE;
TRUNCATE TABLE core_estacaomonta CASCADE;

-- Limpa tabelas de autenticação do Django (opcional - remova o comentário se desejar limpar)
-- TRUNCATE TABLE auth_user CASCADE;
-- TRUNCATE TABLE auth_group CASCADE;
-- TRUNCATE TABLE auth_permission CASCADE;
-- TRUNCATE TABLE django_admin_log CASCADE;
-- TRUNCATE TABLE django_content_type CASCADE;
-- TRUNCATE TABLE django_session CASCADE;

-- Reabilita restrições de chave estrangeira
SET session_replication_role = 'origin';

-- Reinicia as sequências de ID para começar do 1 novamente
-- Isso garante que os IDs de novas inserções comecem do 1
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT sequence_name 
               FROM information_schema.sequences 
               WHERE sequence_schema = 'public'
    LOOP
        EXECUTE 'ALTER SEQUENCE ' || rec.sequence_name || ' RESTART WITH 1';
    END LOOP;
END $$;

-- Reinicia explicitamente as sequências de ID para as tabelas principais
-- Isso é um backup caso o método acima não funcione para alguma sequência específica
ALTER SEQUENCE IF EXISTS core_fazenda_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_animal_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_lote_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_pasto_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_categoriaanimal_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_raca_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_contato_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_despesa_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_contabancaria_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_estacaomonta_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_manejoreproducao_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_categoriacusto_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_subcategoriacusto_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_itemdespesa_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_parceladespesa_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_rateiocusto_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_movimentacaonaooperacional_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS core_extratobancario_id_seq RESTART WITH 1;
