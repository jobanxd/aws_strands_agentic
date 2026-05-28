PRAGMA foreign_keys = ON;

-- ============================================================================
-- DROP TABLES
-- ============================================================================

DROP TABLE IF EXISTS user_odd_review_list;
DROP TABLE IF EXISTS kycnet_drilldown;
DROP TABLE IF EXISTS servicelink_transactions;
DROP TABLE IF EXISTS svoc_extracts;

DROP TABLE IF EXISTS app_user;
DROP TABLE IF EXISTS sharepoint_list;
DROP TABLE IF EXISTS kycnet_reviews;
DROP TABLE IF EXISTS servicelink_account_details;

DROP TABLE IF EXISTS lu_agent_prompts;
DROP TABLE IF EXISTS lu_country_risk_classification;
DROP TABLE IF EXISTS agent_outputs;
DROP TABLE IF EXISTS agent_token_usage;
DROP TABLE IF EXISTS agent_failures;
DROP TABLE IF EXISTS final_report;
DROP TABLE IF EXISTS feedback_table;
DROP TABLE IF EXISTS agent_messages;

-- ============================================================================
-- APP USER
-- ============================================================================

CREATE TABLE app_user (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    modified_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SHAREPOINT LIST
-- ============================================================================

CREATE TABLE sharepoint_list (
    sharepoint_id          INTEGER PRIMARY KEY,
    party_id               TEXT NOT NULL,

    old_review_id          TEXT,
    new_review_id          TEXT,

    risk                   TEXT,
    next_review_date       DATE,
    review_type            TEXT,
    review_status          TEXT,
    review_completion_date DATE,

    modified_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- USER REVIEW LIST
-- ============================================================================

CREATE TABLE user_odd_review_list (
    user_id       INTEGER NOT NULL,
    sharepoint_id INTEGER NOT NULL,

    modified_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_uorl_user
        FOREIGN KEY (user_id)
        REFERENCES app_user (user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_uorl_party
        FOREIGN KEY (sharepoint_id)
        REFERENCES sharepoint_list (sharepoint_id)
        ON DELETE CASCADE
);

-- ============================================================================
-- KYCNET REVIEWS
-- ============================================================================

CREATE TABLE kycnet_reviews (
    review_id                         TEXT PRIMARY KEY,

    entrp_party_ident                 TEXT,
    review_tag                        TEXT,

    type_of_customer                  TEXT,
    business_units                    TEXT,
    previous_review_risk_rating       TEXT,
    title                             TEXT,
    full_name                         TEXT,
    first_name                        TEXT,
    middle_name                       TEXT,
    last_name                         TEXT,
    date_of_birth                     DATE,
    gender                            TEXT,

    address_line_1                    TEXT,
    address_line_2                    TEXT,
    address_line_3                    TEXT,
    post_code                         TEXT,
    country_of_residence              TEXT,
    country_of_birth                  TEXT,
    country_of_citizenship            TEXT,
    length_of_residence               TEXT,

    employment_status                 TEXT,
    occupation                        TEXT,
    employer_name                     TEXT,

    account_type_product              TEXT,
    products_held                     TEXT,
    primary_account_identifier        TEXT,

    cash_income_percentage            TEXT,
    transacted_outside_safe_countries TEXT,
    high_risk_countries_info          TEXT,
    very_high_risk_countries_info     TEXT,
    prohibited_countries_info         TEXT,
    source_funds_wealth_changed       TEXT,
    suspicious_activity_detected      TEXT,
    additional_information            TEXT,
    escalation_required               TEXT,

    modified_at                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- KYCNET DRILLDOWN
-- ============================================================================

CREATE TABLE kycnet_drilldown (
    sharepoint_id               INTEGER NOT NULL,
    review_id                   TEXT NOT NULL,
    party_id                    TEXT NOT NULL,

    entrp_party_ident           TEXT,
    party_name                  TEXT,
    party_type                  TEXT,
    current_review_type         TEXT,
    date_current_review_started DATE,
    current_review_step         TEXT,
    last_manual_risk            TEXT,
    last_automated_risk         TEXT,

    modified_at                 DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_drilldown_review
        FOREIGN KEY (review_id)
        REFERENCES kycnet_reviews (review_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_drilldown_party
        FOREIGN KEY (sharepoint_id)
        REFERENCES sharepoint_list (sharepoint_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================================
-- SERVICELINK ACCOUNT DETAILS
-- ============================================================================

CREATE TABLE servicelink_account_details (
    agmt_id           TEXT PRIMARY KEY,

    account_type      TEXT,
    account_name      TEXT,
    account_address   TEXT,
    post_code         TEXT,
    non_resident_code TEXT,

    modified_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SVOC EXTRACTS
-- ============================================================================

CREATE TABLE svoc_extracts (
    agmt_id           TEXT NOT NULL,

    entrp_party_ident TEXT NOT NULL,
    nsc               TEXT,
    account_no        TEXT,
    con_acct_num      TEXT,

    name              TEXT,
    address           TEXT,
    dob               DATE,
    postcode          TEXT,

    cash_percentage   REAL,
    turnover_selected REAL,

    source_system     TEXT,
    product           TEXT,

    closed            TEXT,
    closure_date      DATE,
    gp_indicator      TEXT,

    modified_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_svoc_account
        FOREIGN KEY (agmt_id)
        REFERENCES servicelink_account_details (agmt_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================================
-- SERVICELINK TRANSACTIONS
-- ============================================================================

CREATE TABLE servicelink_transactions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,

    agmt_id           TEXT NOT NULL,
    account_no        TEXT NOT NULL,
    nsc               TEXT NOT NULL,

    transaction_date  DATE,
    src               TEXT,
    tx_narrative      TEXT,
    debit_eur         REAL,
    credit_eur        REAL,
    tx_code           TEXT,
    country_of_origin TEXT,

    modified_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_transactions_account
        FOREIGN KEY (agmt_id)
        REFERENCES servicelink_account_details (agmt_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================================
-- SUPPORTING TABLES
-- ============================================================================

CREATE TABLE lu_agent_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    agent_name TEXT NOT NULL,
    prompt_index REAL NOT NULL,
    model_name TEXT NOT NULL,
    prompt_description TEXT NOT NULL,
    prompt_content TEXT NOT NULL
);

CREATE TABLE lu_country_risk_classification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    country TEXT NOT NULL,
    risk_classification TEXT NOT NULL
);

CREATE TABLE agent_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    agent_name TEXT NOT NULL,
    session_id TEXT NOT NULL,
    process_id TEXT NOT NULL,

    output_json TEXT NOT NULL,
    summary TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (agent_name, session_id, process_id)
);

CREATE TABLE agent_token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    process_id TEXT NOT NULL,
    agent_name TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    response_preview TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    agent_name TEXT NOT NULL,
    session_id TEXT NOT NULL,
    process_id TEXT NOT NULL,

    reason TEXT,
    recommendation TEXT,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_agent_failures_session_process
    ON agent_failures (session_id, process_id);

CREATE TABLE final_report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    party_id TEXT NOT NULL,
    new_review_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    process_id TEXT NOT NULL,

    overview_summary TEXT,
    next_steps TEXT,

    type_of_customer TEXT,
    account_product TEXT,
    previous_review_risk_rating TEXT,
    title TEXT,
    full_name TEXT,
    dob DATE,
    gender TEXT,
    address TEXT,
    post_code TEXT,
    country_of_residence TEXT,
    country_of_birth TEXT,
    country_of_citizenship TEXT,
    length_of_residence TEXT,
    employment_status TEXT,
    occupation TEXT,
    employer_name TEXT,
    account_type_product TEXT,
    products_held TEXT,
    primary_account_identifier TEXT,

    cash_income_percentage TEXT,
    transacted_outside_safe_countries TEXT,
    high_risk_countries_info TEXT,
    very_high_risk_countries_info TEXT,
    prohibited_countries_info TEXT,
    source_funds_wealth_changed TEXT,
    suspicious_activity_detected TEXT,
    additional_information TEXT,
    escalation_required TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    modified_at DATETIME,
    modified_by TEXT,

    CONSTRAINT unique_party_review
        UNIQUE (party_id, new_review_id, session_id, process_id)
);

CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,

    session_id TEXT NOT NULL,
    process_id TEXT NOT NULL,
    payload TEXT NOT NULL,

    project_id TEXT,
    user_id TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    session_id TEXT NOT NULL,
    review_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    field_name TEXT NOT NULL,

    original_value TEXT NOT NULL,
    new_value TEXT NOT NULL,

    modified_by TEXT,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_session_review
    ON feedback_table(session_id, review_id);

CREATE INDEX idx_feedback_question
    ON feedback_table(question_id);

CREATE INDEX idx_feedback_modified_at
    ON feedback_table(modified_at DESC);