
def validate_data(data):
    data[0] = str(data[0])
    data[1] = str(data[1])
    data[2] = float(data[2])
    data[5] = float(data[5])
    if data[0] != "" and data[1] != "" and data[2] >= 0 and data[3] < data[4] and data[5] >= 0:
        return True
    else:
        return False
