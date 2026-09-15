

CREATE EXTENSION IF NOT EXISTS "pgcrypto";


CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    nome VARCHAR(150) NOT NULL,

    cpf VARCHAR(14) UNIQUE,

    email VARCHAR(150) UNIQUE,

    foto_path TEXT,

    embedding JSONB,

    ativo BOOLEAN NOT NULL DEFAULT TRUE,

    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);



CREATE INDEX IF NOT EXISTS idx_usuarios_nome
ON usuarios(nome);

CREATE INDEX IF NOT EXISTS idx_usuarios_cpf
ON usuarios(cpf);

CREATE INDEX IF NOT EXISTS idx_usuarios_ativo
ON usuarios(ativo);


CREATE TABLE IF NOT EXISTS reconhecimentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    usuario_id UUID,

    foto_path TEXT,

    similaridade NUMERIC(10,6),

    reconhecido BOOLEAN NOT NULL DEFAULT FALSE,

    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_reconhecimento_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE SET NULL
);


CREATE INDEX IF NOT EXISTS idx_reconhecimentos_usuario
ON reconhecimentos(usuario_id);

CREATE INDEX IF NOT EXISTS idx_reconhecimentos_data
ON reconhecimentos(criado_em);


-- =========================================================
-- USUÁRIO DE TESTE
-- =========================================================

-- Opcional: descomente para criar um usuário inicial.
--
-- INSERT INTO usuarios (
--     nome,
--     cpf,
--     email
-- )
-- VALUES (
--     'Usuário Teste',
--     '000.000.000-00',
--     'teste@teste.com'
-- );