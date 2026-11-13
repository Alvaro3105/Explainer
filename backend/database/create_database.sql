CREATE DATABASE IF NOT EXISTS ExplAIner CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ExplAIner;

CREATE TABLE IF NOT EXISTS Aluno (
    id_aluno INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    data_nascimento DATE,
    pontos INT DEFAULT 0,
    foguinho INT DEFAULT 0,
    nick VARCHAR(40),
    minutos_ativos INT NOT NULL DEFAULT 0,
    ultimo_dia_ativo VARCHAR(10),
    sequencia_atual INT NOT NULL DEFAULT 0,
    melhor_sequencia INT NOT NULL DEFAULT 0,
    ultimo_heartbeat DOUBLE,
    segundos_pendentes INT NOT NULL DEFAULT 0,
    termos_aceitos_em DATETIME,
    versao_termos VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Materia (
    id_materia INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(80) NOT NULL UNIQUE,
    nome_busca VARCHAR(80) NOT NULL UNIQUE,
    area VARCHAR(80),
    sinonimos TEXT,
    termos_busca TEXT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Tema (
    id_tema INT AUTO_INCREMENT PRIMARY KEY,
    materia VARCHAR(60) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    id_materia INT,
    id_tema_pai INT,
    nome_busca VARCHAR(160),
    sinonimos TEXT,
    termos_busca TEXT,
    CONSTRAINT uq_tema_materia_nome UNIQUE (id_materia, nome_busca),
    INDEX ix_tema_materia_nome_busca (id_materia, nome_busca),
    INDEX ix_Tema_id_tema_pai (id_tema_pai),
    FOREIGN KEY (id_materia) REFERENCES Materia(id_materia),
    FOREIGN KEY (id_tema_pai) REFERENCES Tema(id_tema)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Questao (
    id_questao INT AUTO_INCREMENT PRIMARY KEY,
    enunciado TEXT NOT NULL,
    alternativa_correta CHAR(1),
    id_tema INT NOT NULL,
    alternativas_json TEXT,
    explicacao TEXT,
    FOREIGN KEY (id_tema) REFERENCES Tema(id_tema)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS desafio (
    id_desafio INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    dificuldade VARCHAR(120) NOT NULL,
    pontuacao INT NOT NULL,
    quantidade_questoes INT,
    data_criacao DATE,
    id_tema INT,
    id_aluno INT,
    nivel_mapa INT NOT NULL DEFAULT 1,
    origem_ia BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (id_tema) REFERENCES Tema(id_tema),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS desafio_questao (
    id_desafio INT NOT NULL,
    id_questao INT NOT NULL,
    PRIMARY KEY (id_desafio, id_questao),
    FOREIGN KEY (id_desafio) REFERENCES desafio(id_desafio),
    FOREIGN KEY (id_questao) REFERENCES Questao(id_questao)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS aluno_desafio (
    id_aluno INT NOT NULL,
    id_desafio INT NOT NULL,
    data_realizacao DATE,
    pontuacao_obtida INT DEFAULT 0,
    concluido BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id_aluno, id_desafio),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_desafio) REFERENCES desafio(id_desafio)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS resposta_desafio (
    id_resposta INT AUTO_INCREMENT PRIMARY KEY,
    id_aluno INT NOT NULL,
    id_desafio INT NOT NULL,
    id_questao INT NOT NULL,
    alternativa_escolhida CHAR(1) NOT NULL,
    correta BOOLEAN NOT NULL DEFAULT FALSE,
    pontos_ganhos INT NOT NULL DEFAULT 0,
    segundos_gastos INT NOT NULL DEFAULT 0,
    data_resposta DATETIME NOT NULL,
    CONSTRAINT uq_resposta_aluno_desafio_questao UNIQUE (id_aluno, id_desafio, id_questao),
    INDEX ix_resposta_desafio_id_aluno (id_aluno),
    INDEX ix_resposta_desafio_id_desafio (id_desafio),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_desafio) REFERENCES desafio(id_desafio),
    FOREIGN KEY (id_questao) REFERENCES Questao(id_questao)
) ENGINE=InnoDB;

-- Pedidos de geração de desafio, usados no limite por aluno.
CREATE TABLE IF NOT EXISTS geracao_desafio (
    id_geracao INT AUTO_INCREMENT PRIMARY KEY,
    id_aluno INT NOT NULL,
    iniciada_em DOUBLE NOT NULL,
    em_andamento BOOLEAN NOT NULL DEFAULT TRUE,
    INDEX ix_geracao_aluno_momento (id_aluno, iniciada_em),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Ranking (
    id_ranking INT AUTO_INCREMENT PRIMARY KEY,
    classificacao INT,
    pontos INT,
    id_aluno INT NOT NULL,
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno)
) ENGINE=InnoDB;

DROP PROCEDURE IF EXISTS sp_ranking_alunos;

DELIMITER //
CREATE PROCEDURE sp_ranking_alunos()
BEGIN
    SELECT Ranking.classificacao, Ranking.pontos, Aluno.nome
    FROM Ranking
    JOIN Aluno ON Ranking.id_aluno = Aluno.id_aluno
    ORDER BY Ranking.pontos DESC, Ranking.classificacao DESC;
END //
DELIMITER ;
