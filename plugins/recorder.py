from plugins.memory_store import save_memory_entry


def record_plain_message(
    *,
    content: str,
    sender: str,
    user_id: int | str,
    group_id: int,
    timestamp: int | float,
) -> bool:
    return save_memory_entry(
        content=content,
        role="user",
        group_id=group_id,
        sender=sender,
        user_id=user_id,
        timestamp=timestamp,
    )
