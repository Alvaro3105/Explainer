CREATE DATABASE IF NOT EXISTS ExplAIner
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ExplAIner;

CREATE TABLE IF NOT EXISTS Aluno (
    id_aluno INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    senha VARCHAR(255) NOT NULL,
    data_nascimento DATE,
    pontos INT DEFAULT 0,
    foguinho INT DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Tema (
    id_tema INT AUTO_INCREMENT PRIMARY KEY,
    materia VARCHAR(60) NOT NULL,
    nome VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Questao (
    id_questao INT AUTO_INCREMENT PRIMARY KEY,
    enunciado TEXT NOT NULL,
    alternativa_correta CHAR(1),
    id_tema INT NOT NULL,
    CONSTRAINT fk_questao_tema FOREIGN KEY (id_tema) REFERENCES Tema(id_tema)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Desafio (
    id_desafio INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    dificuldade VARCHAR(20),
    pontuacao INT,
    quantidade_questoes INT,
    data_criacao DATE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS desafio_questao (
    id_desafio INT,
    id_questao INT,
    PRIMARY KEY (id_desafio, id_questao),
    FOREIGN KEY (id_desafio) REFERENCES Desafio(id_desafio),
    FOREIGN KEY (id_questao) REFERENCES Questao(id_questao)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS aluno_desafio (
    id_aluno INT,
    id_desafio INT,
    data_realizacao DATE,
    pontuacao_obtida INT,
    concluido BOOLEAN,
    PRIMARY KEY (id_aluno, id_desafio),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_desafio) REFERENCES Desafio(id_desafio)
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
    ORDER BY Ranking.pontos DESC, Ranking.classificacao ASC;
END //
DELIMITER ;
