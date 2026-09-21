-- Local development data only. All names and clubs are fictional.
-- Recommended command after migration: python -m app.db.seed
USE club_management;

INSERT INTO users (id, username, password_hash, display_name, status) VALUES
(1, 'student01', 'pbkdf2_sha256$210000$Y2x1Yi1zdHVkZW50MDEwMA==$cludsTLY4pqf-Ax-b9F5JpiyT8UCvexjKRQtDQyTXug=', '学生一', 'NORMAL'),
(2, 'student02', 'pbkdf2_sha256$210000$Y2x1Yi1zdHVkZW50MDIwMA==$SHtblyfMJEEP-54cBoSfFBDRm_KBO4D2BQDuYJC0sWU=', '学生二', 'NORMAL'),
(3, 'leader01', 'pbkdf2_sha256$210000$Y2x1Yi1sZWFkZXIwMTAwMA==$RTFryFKQqCLgb1sT6B2uEtZfsxhEsSHmMmump7u-19w=', '社团负责人一', 'NORMAL'),
(4, 'leader02', 'pbkdf2_sha256$210000$Y2x1Yi1sZWFkZXIwMjAwMA==$2hWMGVu36WXeJYQxu0U6FR6jJY2AwQylSgdwDlWUUN0=', '社团负责人二', 'NORMAL'),
(5, 'manager01', 'pbkdf2_sha256$210000$Y2x1Yi1tYW5hZ2VyMDEwMA==$6IGWIU1JrmRUUUVt33TiVXbtGiM7dMjecPu00fMSVes=', '社团管理人员', 'NORMAL'),
(6, 'admin01', 'pbkdf2_sha256$210000$Y2x1Yi1hZG1pbjAxMDAwMA==$m68qn6OlDkArgg0L-s0cIPJ3blPLNrXaF-qranoLIWs=', '系统管理员', 'NORMAL')
ON DUPLICATE KEY UPDATE display_name=VALUES(display_name);

INSERT IGNORE INTO system_role_assignments (user_id, role_code, active, granted_by) VALUES
(1,'R01',TRUE,6),(2,'R01',TRUE,6),(3,'R01',TRUE,6),(4,'R01',TRUE,6),(5,'R01',TRUE,6),(6,'R01',TRUE,6),
(5,'R03',TRUE,6),(6,'R04',TRUE,6);

INSERT IGNORE INTO club_registration_applications
(id, applicant_user_id, proposed_name, description, review_status, review_comment, reviewed_by, submitted_at, reviewed_at) VALUES
(1,3,'星河读书社','虚构测试社团','APPROVED','Seed approval',5,NOW(),NOW()),
(2,4,'像素创意社','虚构测试社团','APPROVED','Seed approval',5,NOW(),NOW()),
(3,3,'晨风运动社','虚构测试社团','APPROVED','Seed approval',5,NOW(),NOW()),
(4,1,'纸飞机兴趣社','草稿测试','DRAFT',NULL,NULL,NULL,NULL),
(5,1,'逻辑谜题社','待审核测试','PENDING',NULL,NULL,NOW(),NULL),
(6,2,'远山摄影社','驳回测试','REJECTED','测试材料不完整',5,NOW(),NOW());

INSERT IGNORE INTO clubs (id, registration_application_id, name, description) VALUES
(1,1,'星河读书社','虚构测试社团'),(2,2,'像素创意社','虚构测试社团'),(3,3,'晨风运动社','虚构测试社团');

INSERT IGNORE INTO club_role_assignments (user_id, club_id, role_code, active, granted_by) VALUES
(3,1,'R02',TRUE,5),(4,2,'R02',TRUE,5),(3,3,'R02',TRUE,5);
INSERT IGNORE INTO club_members (club_id,user_id,position_name,status) VALUES
(1,3,'负责人','ACTIVE'),(2,4,'负责人','ACTIVE'),(3,3,'负责人','ACTIVE'),(1,1,'成员','ACTIVE');

INSERT IGNORE INTO annual_review_applications
(club_id,review_year,submitted_by,materials,review_status,review_comment,reviewed_by,submitted_at,reviewed_at) VALUES
(1,2023,3,'年审草稿','DRAFT',NULL,NULL,NULL,NULL),
(1,2024,3,'年审待审核','PENDING',NULL,NULL,NOW(),NULL),
(1,2025,3,'年审已通过','APPROVED','Seed review',5,NOW(),NOW()),
(1,2026,3,'年审已驳回','REJECTED','Seed review',5,NOW(),NOW());

INSERT IGNORE INTO activities
(id,club_id,created_by,title,description,location,starts_at,ends_at,registration_deadline,capacity,budget,review_status,execution_status,cancellation_reason) VALUES
(1,1,3,'未发布读书会','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 2 DAY),DATE_ADD(NOW(),INTERVAL 50 HOUR),DATE_ADD(NOW(),INTERVAL 1 DAY),30,100,'APPROVED','UNPUBLISHED',NULL),
(2,2,4,'开放报名创意展','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 3 DAY),DATE_ADD(NOW(),INTERVAL 74 HOUR),DATE_ADD(NOW(),INTERVAL 2 DAY),30,100,'APPROVED','REGISTRATION_OPEN',NULL),
(3,1,3,'已结束分享会','虚构 Seed 活动','测试场地',DATE_SUB(NOW(),INTERVAL 2 DAY),DATE_SUB(NOW(),INTERVAL 46 HOUR),NULL,30,100,'APPROVED','ENDED',NULL),
(4,3,3,'已取消晨跑','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 4 DAY),DATE_ADD(NOW(),INTERVAL 98 HOUR),NULL,30,100,'APPROVED','CANCELLED','Seed cancellation'),
(5,1,3,'活动草稿','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 5 DAY),DATE_ADD(NOW(),INTERVAL 122 HOUR),NULL,30,100,'DRAFT','UNPUBLISHED',NULL),
(6,2,4,'待审核活动','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 6 DAY),DATE_ADD(NOW(),INTERVAL 146 HOUR),NULL,30,100,'PENDING','UNPUBLISHED',NULL),
(7,1,3,'已驳回活动','虚构 Seed 活动','测试场地',DATE_ADD(NOW(),INTERVAL 7 DAY),DATE_ADD(NOW(),INTERVAL 170 HOUR),NULL,30,100,'REJECTED','UNPUBLISHED',NULL);
INSERT IGNORE INTO activity_registrations (activity_id,user_id,status) VALUES (2,1,'REGISTERED');

INSERT IGNORE INTO finance_records
(id,club_id,activity_id,record_type,amount,occurred_on,description,status,created_by,voided_by,void_reason) VALUES
(1,1,NULL,'INCOME',500,NOW(),'虚构会费收入','ACTIVE',3,NULL,NULL),
(2,1,1,'EXPENSE',88,NOW(),'虚构活动材料支出','ACTIVE',3,NULL,NULL),
(3,2,NULL,'EXPENSE',20,NOW(),'虚构作废记录','VOIDED',4,4,'Seed void');
INSERT IGNORE INTO notifications (recipient_user_id,title,content,event_type,read_status,read_at) VALUES
(1,'报名成功','虚构通知：活动报名成功','ACTIVITY_REGISTRATION','UNREAD',NULL),
(3,'审核结果','虚构通知：申请已通过','REVIEW_RESULT','READ',NOW());
