-- oyuKids schema for SingleStore. Applied by `python -m scripts.init_db`.

CREATE TABLE IF NOT EXISTS kids (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(64)  NOT NULL,
    avatar       VARCHAR(16)  NOT NULL DEFAULT '🦊',
    grade        TINYINT      NOT NULL DEFAULT 1,
    streak_days  INT          NOT NULL DEFAULT 0,
    created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS passages (
    id        BIGINT AUTO_INCREMENT PRIMARY KEY,
    title     VARCHAR(255) NOT NULL,
    category  VARCHAR(16)  NOT NULL,          -- essay | novel | quote | tale
    level     TINYINT      NOT NULL DEFAULT 1, -- 1..3
    body      TEXT         NOT NULL,
    source    VARCHAR(255) NOT NULL DEFAULT '',
    emoji     VARCHAR(16)  NOT NULL DEFAULT '📖'
);

CREATE TABLE IF NOT EXISTS poems (
    id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    title   VARCHAR(255) NOT NULL,
    author  VARCHAR(255) NOT NULL,
    level   TINYINT      NOT NULL DEFAULT 1,
    body    TEXT         NOT NULL,             -- one line per verse line
    emoji   VARCHAR(16)  NOT NULL DEFAULT '📝'
);

CREATE TABLE IF NOT EXISTS compound_words (
    id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    phrase  VARCHAR(128) NOT NULL,             -- холбоо үг, e.g. 'ном дэвтэр'
    level   TINYINT      NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS word_rounds (
    id               CHAR(32)    NOT NULL PRIMARY KEY,
    kid_id           BIGINT      NOT NULL,
    level            VARCHAR(16) NOT NULL,
    words            JSON        NOT NULL,     -- ordered list of phrases shown
    display_seconds  INT         NOT NULL,
    created_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS attempts (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    kid_id       BIGINT       NOT NULL,
    activity     VARCHAR(16)  NOT NULL,        -- reading | words | poems
    item_id      VARCHAR(64)  NOT NULL,
    item_title   VARCHAR(255) NOT NULL,
    transcript   TEXT         NOT NULL,
    duration_ms  INT          NOT NULL,
    score        DOUBLE       NOT NULL,        -- 0..1
    stars        TINYINT      NOT NULL,        -- 0..3
    wpm          DOUBLE       NULL,
    details      JSON         NULL,
    created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    SORT KEY (created_at)
);
