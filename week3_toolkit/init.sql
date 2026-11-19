SET NAMES utf8mb4;
-- 创建数据库时强制指定字符集
CREATE DATABASE IF NOT EXISTS emotion_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE emotion_db;

-- 创建表时强制指定字符集
CREATE TABLE IF NOT EXISTS healing_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    emotion VARCHAR(20),
    message VARCHAR(255)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(32) NOT NULL,
    display_name VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 创建心情表
CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_auth_sessions_token (token_hash),
    KEY idx_auth_sessions_user (user_id),
    KEY idx_auth_sessions_expires (expires_at),
    CONSTRAINT fk_auth_sessions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

ALTER TABLE diaries
    ADD CONSTRAINT fk_diaries_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE;

-- 创建日记表
CREATE TABLE IF NOT EXISTS diaries (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NULL,
    visual_emotion VARCHAR(20) NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    text_content TEXT NOT NULL,
    healing_message VARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    PRIMARY KEY (id),
    INDEX idx_diaries_user_created (user_id, created_at),
    INDEX idx_diaries_created (created_at),
    CONSTRAINT fk_diaries_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 创建个人介绍和头像地址表
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT UNSIGNED NOT NULL,
    bio VARCHAR(500) NOT NULL DEFAULT '',
    avatar_url VARCHAR(500) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_user_profiles_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO user_profiles (user_id)
SELECT id FROM users;
-- 创建心情动态、情绪标签和可见范围表
CREATE TABLE IF NOT EXISTS posts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    content TEXT NOT NULL,
    mood VARCHAR(20) NULL,
    visibility ENUM('private', 'public')
        NOT NULL DEFAULT 'private',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_posts_user_created (user_id, created_at),
    KEY idx_posts_public_created (visibility, created_at),
    KEY idx_posts_created (created_at),
    CONSTRAINT fk_posts_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
--创建动态评论表
CREATE TABLE IF NOT EXISTS post_comments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    content VARCHAR(1000) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_post_comments_post_created (post_id, created_at),
    KEY idx_post_comments_user_created (user_id, created_at),
    CONSTRAINT fk_post_comments_post
        FOREIGN KEY (post_id) REFERENCES posts (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_post_comments_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

--创建点赞表。一个用户对一条动态只能点赞一次。
CREATE TABLE IF NOT EXISTS post_reactions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    post_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    reaction_type VARCHAR(16) NOT NULL DEFAULT 'like',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_post_reaction_user (post_id, user_id),
    KEY idx_post_reactions_user (user_id, created_at),
    CONSTRAINT fk_post_reactions_post
        FOREIGN KEY (post_id) REFERENCES posts (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_post_reactions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 插入数据（保持原样，因为文件本身已经是 UTF-8 了）
INSERT INTO healing_messages (emotion, message) VALUES ('neutral', '你今天看起来很平静，继续保持这份从容哦！');
INSERT INTO healing_messages (emotion, message) VALUES ('happy', '看到你开心的样子，世界都变明亮了！');
INSERT INTO healing_messages (emotion, message) VALUES ('sad', '难过的时候可以休息一下，我会一直在这里陪着你。');
INSERT INTO healing_messages (emotion, message) VALUES ('angry', '深呼吸，也许出去散个步能帮你平复心情。');
INSERT INTO healing_messages (emotion, message) VALUES ('fear', '别担心，你很勇敢，事情都会好起来的。');

INSERT INTO `healing_messages`(`emotion`, `message`) VALUES
  ('happiness', '太棒了！你的笑容仿佛能融化一切阴霾，请继续保持这份光芒。'),
  ('happiness', '今天是个值得庆祝的日子，去吃点好吃的犒劳一下自己吧！'),
  ('happiness', '快乐是会传染的，谢谢你让这个屏幕前的我也感受到了温暖。'),
  ('happiness', '春风得意马蹄疾！带着这份好心情，去挑战今天的所有任务吧。'),
  ('sadness', '没关系的，雨总会停的，天总会晴的。在这个小角落里，你可以卸下所有防备。'),
  ('sadness', '允许自己有一段低谷期，就像植物在冬天积蓄能量，为了春天的绽放。'),
  ('sadness', '如果觉得累了，就闭上眼睛休息一会儿。不要对自己太苛刻了。'),
  ('sadness', '你的情绪很珍贵，不必为了迎合别人而强颜欢笑，我在听。'),
  ('anger', '先深呼吸——吸气，呼气。不要用别人的错误来惩罚这么可爱的自己。'),
  ('anger', '我知道你现在感觉快气炸了，去喝杯冰水，或者找个枕头揍两拳释放一下吧！'),
  ('anger', '愤怒说明你的底线被触碰了，这很正常。但发火后，记得抱抱自己。'),
  ('anger', '如果实在很生气，不如把惹你生气的事情写在纸上，然后狠狠地撕碎它！'),
  ('neutral', '此时此刻，无风无雨，正是一个绝佳的思考与放空的时间。'),
  ('neutral', '平静的湖面下蕴藏着巨大的能量。享受这片刻的宁静吧。'),
  ('neutral', '不喜不悲也是一种极高的境界，愿你能在平凡中发现微小的确幸。'),
  ('neutral', '专注当下，倾听自己的呼吸，现在的你处于最理智、最高效的状态。'),
  ('surprise', '哇哦！生活就像一盒巧克力，对吧？好好享受这个意料之外的时刻！'),
  ('surprise', '瞪大眼睛的你很有趣！既然意外已经发生，不如把它当成一场冒险。'),
  ('surprise', '打破常规的惊喜总是让人精神一振，希望这是个让你开心的意外。'),
  ('fear', '感到害怕是人类的本能，这说明你在保护自己。不要怕，现在的你很安全。'),
  ('fear', '无论你在恐惧什么，想象我正隔着屏幕给你披上一件保暖的毯子，给你传递勇气。'),
  ('fear', '恐惧往往来源于未知。试着把害怕的事情拆解开来，你会发现它没那么不可战胜。'),
  ('disgust', '快把视线移开！去看看美丽的风景，或者听一首喜欢的歌洗洗眼睛和耳朵。'),
  ('disgust', '遇到厌恶的人或事，最好的反击就是保持自己的优雅，然后彻底无视它。'),
  ('disgust', '给自己喷点喜欢的香水，或者点个香薰，把不好的感觉全都隔离在安全线之外吧！'),
  ('happiness', '笑容是最美的风景，希望你的快乐能感染更多人！'),
  ('happiness', '今天看起来心情大好哦！把这份热情传递下去吧。'),
  ('happiness', '看到你开心，世界都变得明亮了起来✨'),
  ('sadness', '今天也要抱抱自己哦，允许自己偶尔低落，我在这里陪你。'),
  ('sadness', '乌云总会散去，难过的时候去吃点甜的吧🍬'),
  ('sadness', '不想笑的时候可以不笑，你的每一面都很珍贵。'),
  ('anger', '气呼呼的也可爱，但别让坏情绪伤了身体，喝杯温水放松一下吧。'),
  ('anger', '是谁惹你生气了？深呼吸三次，把坏心情呼出去💨'),
  ('anger', '生气是用别人的错误惩罚自己，去听首喜欢的歌缓缓吧。'),
  ('neutral', '平和是最有力量的状态，享受这专属于你的宁静时刻。'),
  ('neutral', '心静如水，不骄不躁，现在的你拥有绝对的专注力。'),
  ('neutral', '普通的一天也很棒，平平淡淡才是生活的底色🍃'),
  ('surprise', '生活中总是充满意想不到的小插曲，深呼吸，去迎接它吧！'),
  ('fear', '别怕，勇敢不是不害怕，而是带着恐惧继续前行。'),
  ('disgust', '遇到不喜欢的事物就稍微保持距离吧，你的感受最重要。');

CREATE TABLE IF NOT EXISTS user_emails (
    user_id BIGINT UNSIGNED NOT NULL,
    email VARCHAR(254) NOT NULL,
    verified_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_emails_email (email),
    CONSTRAINT fk_user_emails_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    email VARCHAR(254) NOT NULL,
    token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email_verification_token (token_hash),
    KEY idx_email_verification_user (user_id, created_at),
    KEY idx_email_verification_expires (expires_at),
    CONSTRAINT fk_email_verification_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_token (token_hash),
    KEY idx_password_reset_user (user_id, created_at),
    KEY idx_password_reset_expires (expires_at),
    CONSTRAINT fk_password_reset_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(80) NOT NULL DEFAULT '新的对话',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_chat_sessions_user_updated (user_id, updated_at),
    CONSTRAINT fk_chat_sessions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id BIGINT UNSIGNED NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    safety_flag TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_chat_messages_session_created (session_id, created_at),
    CONSTRAINT fk_chat_messages_session
        FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
