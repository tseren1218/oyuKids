-- oyuKids schema for SingleStore. Applied by `python -m scripts.init_db`.
-- Note: SingleStore unique keys must contain the shard key, so uniqueness of
-- users.username and classrooms.join_code is enforced by the application.
-- attempts/word_rounds keep the original `kid_id` column name (= users.id of the student).

CREATE TABLE IF NOT EXISTS users (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    role         VARCHAR(16)  NOT NULL,          -- student | teacher
    username     VARCHAR(64)  NOT NULL,
    name         VARCHAR(128) NOT NULL,
    avatar       VARCHAR(16)  NOT NULL DEFAULT '🦊',
    grade        TINYINT      NULL,
    streak_days  INT          NOT NULL DEFAULT 0,
    created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY (username)
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

CREATE TABLE IF NOT EXISTS classrooms (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    teacher_id  BIGINT       NOT NULL,
    name        VARCHAR(128) NOT NULL,
    grade       TINYINT      NOT NULL,
    emoji       VARCHAR(16)  NOT NULL DEFAULT '🌻',
    join_code   VARCHAR(16)  NOT NULL,
    created_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY (teacher_id),
    KEY (join_code)
);

CREATE TABLE IF NOT EXISTS memberships (
    classroom_id  BIGINT      NOT NULL,
    student_id    BIGINT      NOT NULL,
    status        VARCHAR(16) NOT NULL,        -- invited | active
    created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (classroom_id, student_id),
    KEY (student_id)
);

CREATE TABLE IF NOT EXISTS assignments (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    classroom_id  BIGINT       NOT NULL,
    activity      VARCHAR(16)  NOT NULL,       -- reading | words | poems
    item_id       VARCHAR(64)  NOT NULL,       -- passage id · poem id · words level
    title         VARCHAR(255) NOT NULL,
    due_date      DATE         NOT NULL,
    instructions  TEXT         NOT NULL,
    created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY (classroom_id)
);

CREATE TABLE IF NOT EXISTS word_rounds (
    id               CHAR(32)    NOT NULL PRIMARY KEY,
    kid_id           BIGINT      NOT NULL,
    level            VARCHAR(16) NOT NULL,
    words            JSON        NOT NULL,     -- ordered list of phrases shown
    display_seconds  INT         NOT NULL,
    assignment_id    BIGINT      NULL,
    created_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
);

CREATE TABLE IF NOT EXISTS attempts (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    kid_id         BIGINT       NOT NULL,
    activity       VARCHAR(16)  NOT NULL,      -- reading | words | poems
    item_id        VARCHAR(64)  NOT NULL,
    item_title     VARCHAR(255) NOT NULL,
    transcript     TEXT         NOT NULL,
    duration_ms    INT          NOT NULL,
    score          DOUBLE       NOT NULL,      -- 0..1
    stars          TINYINT      NOT NULL,      -- 0..3
    wpm            DOUBLE       NULL,
    details        JSON         NULL,
    assignment_id  BIGINT       NULL,
    audio_url      VARCHAR(1024) NULL,         -- s3://… WAV of the child's recording
    created_at     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY (kid_id),
    KEY (assignment_id),
    SORT KEY (created_at)
);
