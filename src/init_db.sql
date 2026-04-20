-- ============================================================
-- AIgorithm_Agent 数据库初始化 SQL (MySQL 版本)
--
-- 使用方式:
--   mysql -u root -p < init_db.sql
--   或在 MySQL 客户端中执行: source init_db.sql
--
-- 说明:
--   本项目默认使用 SQLite (database.py)，
--   此文件为需要 MySQL 部署的场景提供等价建表语句。
-- ============================================================

-- 第一部分: 创建数据库和用户
CREATE DATABASE IF NOT EXISTS `AIgorithm_Agent`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'AIgorithm_Agent'@'localhost' IDENTIFIED BY '123456';
CREATE USER IF NOT EXISTS 'AIgorithm_Agent'@'%' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON `AIgorithm_Agent`.* TO 'AIgorithm_Agent'@'localhost';
GRANT ALL PRIVILEGES ON `AIgorithm_Agent`.* TO 'AIgorithm_Agent'@'%';
FLUSH PRIVILEGES;

USE `AIgorithm_Agent`;

-- 第二部分: 建表

-- 聊天会话表
CREATE TABLE IF NOT EXISTS `chat_session` (
    `session_id`   VARCHAR(64) NOT NULL PRIMARY KEY,
    `user_id`      VARCHAR(128) NOT NULL,
    `title`        VARCHAR(256) NOT NULL,
    `last_message` VARCHAR(512) DEFAULT NULL,
    `course_id`    VARCHAR(64) DEFAULT NULL,
    `created_at`   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at`   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 引用来源表
CREATE TABLE IF NOT EXISTS `citation` (
    `citation_id`  VARCHAR(64) NOT NULL PRIMARY KEY,
    `source_type`  VARCHAR(20) NOT NULL COMMENT 'TEXTBOOK|WEBPAGE|QUESTION_BANK|KNOWLEDGE_POINT|OTHER',
    `source_title` VARCHAR(512) NOT NULL,
    `location`     VARCHAR(256) DEFAULT NULL,
    `snippet`      TEXT DEFAULT NULL,
    `document_id`  VARCHAR(64) DEFAULT NULL,
    `chunk_id`     VARCHAR(64) DEFAULT NULL,
    `created_at`   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天消息表
CREATE TABLE IF NOT EXISTS `chat_message` (
    `id`                VARCHAR(64) NOT NULL PRIMARY KEY,
    `session_id`        VARCHAR(64) NOT NULL,
    `role`              VARCHAR(10) NOT NULL COMMENT 'USER|ASSISTANT',
    `content`           LONGTEXT NOT NULL,
    `parent_message_id` VARCHAR(64) DEFAULT NULL,
    `timestamp`         DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_message_session` FOREIGN KEY (`session_id`)
        REFERENCES `chat_session` (`session_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_message_parent` FOREIGN KEY (`parent_message_id`)
        REFERENCES `chat_message` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 消息-引用关联表
CREATE TABLE IF NOT EXISTS `message_citation` (
    `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
    `message_id`      VARCHAR(64) NOT NULL,
    `citation_id`     VARCHAR(64) NOT NULL,
    `citation_number` INT NOT NULL,
    CONSTRAINT `fk_mc_message` FOREIGN KEY (`message_id`)
        REFERENCES `chat_message` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_mc_citation` FOREIGN KEY (`citation_id`)
        REFERENCES `citation` (`citation_id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_message_citation_number` (`message_id`, `citation_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 第三部分: 索引
CREATE INDEX `idx_session_user_id`    ON `chat_session` (`user_id`);
CREATE INDEX `idx_session_course_id`  ON `chat_session` (`course_id`);
CREATE INDEX `idx_session_updated_at` ON `chat_session` (`updated_at` DESC);
CREATE INDEX `idx_message_session_ts` ON `chat_message` (`session_id`, `timestamp`);
CREATE INDEX `idx_mc_message_id`      ON `message_citation` (`message_id`);

-- 第四部分: 常用 CRUD 示例
--
-- 列出某用户会话:
--   SELECT * FROM chat_session WHERE user_id='xxx' ORDER BY updated_at DESC;
--
-- 获取会话消息及引用:
--   SELECT m.*, c.source_title, c.source_type, mc.citation_number
--   FROM chat_message m
--   LEFT JOIN message_citation mc ON m.id = mc.message_id
--   LEFT JOIN citation c ON mc.citation_id = c.citation_id
--   WHERE m.session_id = 'SESSION_ID'
--   ORDER BY m.timestamp;
--
-- 创建会话:
--   INSERT INTO chat_session (session_id, user_id, title) VALUES (UUID(), 'user1', '新对话');
--
-- 删除会话(级联):
--   DELETE FROM chat_session WHERE session_id = 'xxx';

SELECT '数据库初始化完成!' AS status;
