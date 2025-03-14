-- Remover a restrição de unicidade existente no campo brinco_eletronico
ALTER TABLE core_animal DROP CONSTRAINT IF EXISTS core_animal_brinco_eletronico_key;

-- Criar um novo índice que garante unicidade do brinco_eletronico por usuário,
-- mas apenas quando o brinco_eletronico não for NULL
CREATE UNIQUE INDEX core_animal_brinco_eletronico_usuario_unique 
ON core_animal (brinco_eletronico, usuario_id) 
WHERE brinco_eletronico IS NOT NULL;
