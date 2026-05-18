from datetime import datetime

def validate_data(data):
    try:
        # Strings
        field0 = str(data[0]).strip()

        # Unit ID (int from QComboBox)
        field1 = int(data[1])

        # Numbers
        field2 = float(data[2]) if data[2] != '' else 0.0
        field5 = float(data[5]) if data[5] != '' else 0.0

        # Dates (IMPORTANT)
        field3 = datetime.strptime(data[3], "%Y-%m-%d") if data[3] != '' else None
        field4 = datetime.strptime(data[4], "%Y-%m-%d")

        # Validation
        if (
            field0 != "" and
            field1 >= 1 and
            field2 >= 0 and
            field3 is not None and
            field3 < field4 and
            field5 >= 0
        ):
            return True
        else:
            return False

    except (ValueError, IndexError):
        return False