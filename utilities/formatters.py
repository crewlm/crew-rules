from datetime import timedelta


def format_field(entity_name: str, field: str):
    # if entity_name:
    #     field = entity_name + "." + field
    field = "input_entity." + field
    field = field.replace("s.", "s' ").replace(".", "'s ").replace("_", " ")
    # if not field:
    #     return field
    return field[0].upper() + field[1:]


def timedelta_to_iso8601(td: timedelta) -> str:
    # Extract total seconds and handle negative durations if necessary
    total_seconds = int(td.total_seconds())
    days = td.days

    # Extract hours, minutes, and seconds from the remaining seconds of the day
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60
    seconds = remaining_seconds % 60

    # Build date and time components
    date_part = f"{days}D" if days else ""
    time_part = ""
    if hours or minutes or seconds:
        time_part = "T"
        if hours:
            time_part += f"{hours}H"
        if minutes:
            time_part += f"{minutes}M"
        if seconds:
            time_part += f"{seconds}S"

    return f"P{date_part}{time_part}"
