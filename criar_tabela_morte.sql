CREATE TABLE IF NOT EXISTS core_registromorte (
    id SERIAL PRIMARY KEY,
    data_morte DATE NOT NULL,
    observacao TEXT,
    prejuizo NUMERIC(10, 2) NOT NULL DEFAULT 0,
    data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    animal_id INTEGER NOT NULL REFERENCES core_animal(id),
    motivo_id INTEGER NOT NULL REFERENCES core_motivomorte(id),
    usuario_id INTEGER NOT NULL REFERENCES auth_user(id)
);

COMMENT ON TABLE core_registromorte IS 'Registros de morte de animais';
COMMENT ON COLUMN core_registromorte.data_morte IS 'Data da morte do animal';
COMMENT ON COLUMN core_registromorte.observacao IS 'Observações sobre a morte';
COMMENT ON COLUMN core_registromorte.prejuizo IS 'Valor do prejuízo causado pela morte';
COMMENT ON COLUMN core_registromorte.data_registro IS 'Data e hora do registro';
COMMENT ON COLUMN core_registromorte.data_atualizacao IS 'Data e hora da última atualização';
COMMENT ON COLUMN core_registromorte.animal_id IS 'Referência ao animal que morreu';
COMMENT ON COLUMN core_registromorte.motivo_id IS 'Referência ao motivo da morte';
COMMENT ON COLUMN core_registromorte.usuario_id IS 'Referência ao usuário que registrou a morte';

-- Cria índices para melhorar o desempenho
CREATE INDEX IF NOT EXISTS core_registromorte_animal_id ON core_registromorte(animal_id);
CREATE INDEX IF NOT EXISTS core_registromorte_motivo_id ON core_registromorte(motivo_id);
CREATE INDEX IF NOT EXISTS core_registromorte_usuario_id ON core_registromorte(usuario_id);
CREATE INDEX IF NOT EXISTS core_registromorte_data_morte ON core_registromorte(data_morte);
