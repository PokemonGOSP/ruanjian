-- MySQL 8 reference schema for Engineering Skeleton V0.1.
-- Preferred creation path: cd backend && alembic upgrade head
CREATE DATABASE IF NOT EXISTS club_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE club_management;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  status ENUM('NORMAL','DISABLED') NOT NULL DEFAULT 'NORMAL',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS system_role_assignments (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  role_code VARCHAR(3) NOT NULL COMMENT 'R01/R03/R04; R02 belongs in club_role_assignments',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  granted_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_user_system_role UNIQUE (user_id, role_code),
  CONSTRAINT fk_system_role_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_system_role_granter FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS club_registration_applications (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  applicant_user_id BIGINT NOT NULL,
  proposed_name VARCHAR(150) NOT NULL,
  description TEXT NOT NULL,
  advisor_contact VARCHAR(255) NULL,
  review_status ENUM('DRAFT','PENDING','APPROVED','REJECTED','WITHDRAWN') NOT NULL DEFAULT 'DRAFT',
  review_comment TEXT NULL,
  reviewed_by BIGINT NULL,
  submitted_at DATETIME NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_club_registration_applicant (applicant_user_id),
  INDEX ix_club_registration_status (review_status),
  CONSTRAINT fk_club_registration_applicant FOREIGN KEY (applicant_user_id) REFERENCES users(id),
  CONSTRAINT fk_club_registration_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS clubs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  registration_application_id BIGINT NOT NULL UNIQUE,
  name VARCHAR(150) NOT NULL UNIQUE,
  description TEXT NOT NULL,
  advisor_contact VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_club_registration FOREIGN KEY (registration_application_id) REFERENCES club_registration_applications(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS club_role_assignments (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  club_id BIGINT NOT NULL,
  role_code VARCHAR(3) NOT NULL DEFAULT 'R02',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  granted_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_user_club_role UNIQUE (user_id, club_id, role_code),
  CONSTRAINT fk_club_role_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_club_role_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_club_role_granter FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS annual_review_applications (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  club_id BIGINT NOT NULL,
  review_year INT NOT NULL,
  submitted_by BIGINT NOT NULL,
  materials TEXT NOT NULL,
  review_status ENUM('DRAFT','PENDING','APPROVED','REJECTED','WITHDRAWN') NOT NULL DEFAULT 'DRAFT',
  review_comment TEXT NULL,
  reviewed_by BIGINT NULL,
  submitted_at DATETIME NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_club_review_year UNIQUE (club_id, review_year),
  CONSTRAINT fk_annual_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_annual_submitter FOREIGN KEY (submitted_by) REFERENCES users(id),
  CONSTRAINT fk_annual_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS club_members (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  club_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  position_name VARCHAR(100) NULL,
  status ENUM('ACTIVE','EXITED') NOT NULL DEFAULT 'ACTIVE',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  exited_at DATETIME NULL,
  CONSTRAINT uq_club_member UNIQUE (club_id, user_id),
  CONSTRAINT fk_member_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_member_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS membership_applications (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  club_id BIGINT NOT NULL,
  applicant_user_id BIGINT NOT NULL,
  application_type ENUM('JOIN','EXIT') NOT NULL,
  reason TEXT NULL,
  status ENUM('PENDING','APPROVED','REJECTED','WITHDRAWN') NOT NULL DEFAULT 'PENDING',
  processed_by BIGINT NULL,
  process_comment TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at DATETIME NULL,
  CONSTRAINT fk_membership_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_membership_applicant FOREIGN KEY (applicant_user_id) REFERENCES users(id),
  CONSTRAINT fk_membership_processor FOREIGN KEY (processed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activities (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  club_id BIGINT NOT NULL,
  created_by BIGINT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  location VARCHAR(255) NOT NULL,
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  registration_deadline DATETIME NULL,
  capacity INT NULL,
  budget DECIMAL(12,2) NOT NULL DEFAULT 0,
  review_status ENUM('DRAFT','PENDING','APPROVED','REJECTED','WITHDRAWN') NOT NULL DEFAULT 'DRAFT',
  execution_status ENUM('UNPUBLISHED','REGISTRATION_OPEN','REGISTRATION_CLOSED','IN_PROGRESS','ENDED','CANCELLED') NOT NULL DEFAULT 'UNPUBLISHED',
  review_comment TEXT NULL,
  reviewed_by BIGINT NULL,
  cancellation_reason TEXT NULL,
  summary TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_activity_club (club_id),
  INDEX ix_activity_review_status (review_status),
  INDEX ix_activity_execution_status (execution_status),
  CONSTRAINT fk_activity_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_activity_creator FOREIGN KEY (created_by) REFERENCES users(id),
  CONSTRAINT fk_activity_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS activity_registrations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  activity_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  status ENUM('REGISTERED','CANCELLED') NOT NULL DEFAULT 'REGISTERED',
  registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cancelled_at DATETIME NULL,
  CONSTRAINT uq_activity_registration UNIQUE (activity_id, user_id),
  CONSTRAINT fk_activity_registration_activity FOREIGN KEY (activity_id) REFERENCES activities(id),
  CONSTRAINT fk_activity_registration_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS finance_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  club_id BIGINT NOT NULL,
  activity_id BIGINT NULL,
  record_type ENUM('INCOME','EXPENSE') NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  occurred_on DATETIME NOT NULL,
  description VARCHAR(500) NOT NULL,
  voucher_reference VARCHAR(255) NULL,
  status ENUM('ACTIVE','VOIDED') NOT NULL DEFAULT 'ACTIVE',
  created_by BIGINT NOT NULL,
  voided_by BIGINT NULL,
  void_reason TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_finance_club FOREIGN KEY (club_id) REFERENCES clubs(id),
  CONSTRAINT fk_finance_activity FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL,
  CONSTRAINT fk_finance_creator FOREIGN KEY (created_by) REFERENCES users(id),
  CONSTRAINT fk_finance_voider FOREIGN KEY (voided_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notifications (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  recipient_user_id BIGINT NOT NULL,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  related_type VARCHAR(50) NULL,
  related_id BIGINT NULL,
  read_status ENUM('UNREAD','READ') NOT NULL DEFAULT 'UNREAD',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  read_at DATETIME NULL,
  INDEX ix_notification_recipient (recipient_user_id),
  INDEX ix_notification_read_status (read_status),
  CONSTRAINT fk_notification_recipient FOREIGN KEY (recipient_user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  actor_user_id BIGINT NULL,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(100) NOT NULL,
  resource_id VARCHAR(64) NULL,
  detail_json TEXT NULL,
  ip_address VARCHAR(45) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_audit_actor (actor_user_id),
  INDEX ix_audit_action (action),
  INDEX ix_audit_created_at (created_at),
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS revoked_tokens (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  jti VARCHAR(36) NOT NULL UNIQUE,
  user_id BIGINT NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_revoked_token_expires (expires_at),
  CONSTRAINT fk_revoked_token_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;
