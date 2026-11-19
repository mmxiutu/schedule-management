from __future__ import annotations

TYPE_TASK = "task"
TYPE_RECURRING = "recurring_task"
TYPE_NOTE = "note"
TYPE_PROJECT = "project"
TYPE_SETTINGS = "settings"

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"

KIND_NORMAL = "normal"
KIND_RECURRING = "recurring_instance"

SETTINGS_ID = "settings"

STATUS_LABELS = {
    STATUS_NOT_STARTED: "未开始",
    STATUS_IN_PROGRESS: "进行中",
    STATUS_DONE: "已完成",
}

KIND_LABELS = {
    KIND_NORMAL: "普通任务",
    KIND_RECURRING: "周期任务",
}
