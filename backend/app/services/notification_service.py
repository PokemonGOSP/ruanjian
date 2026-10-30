"""FR-19 站内通知的写入入口。

M06 的查询、已读和管理通知 API 由 Member C 实现；本模块只负责 M04 业务事件
（提交、审核、报名、取消报名、活动取消）生成站内通知记录，不定义外部通知渠道。
"""

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.db.models.domain import Notification, ReadStatus


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify_users(
        self,
        user_ids: Iterable[int],
        *,
        title: str,
        content: str,
        event_type: str,
        related_id: int | None = None,
    ) -> int:
        recipients = sorted({int(user_id) for user_id in user_ids})
        for recipient_id in recipients:
            self.db.add(
                Notification(
                    recipient_user_id=recipient_id,
                    title=title[:200],
                    content=content,
                    event_type=event_type,
                    related_type="ACTIVITY",
                    related_id=related_id,
                    read_status=ReadStatus.UNREAD,
                )
            )
        return len(recipients)
