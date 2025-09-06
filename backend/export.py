def export_csv(result: list[dict]):
    """
    Export the given result as a JSON string.
    Parameters:
        result (list[dict]): The data to be exported.
    Returns:
        dict: A dictionary containing the success status and the JSON string or an error message.
    """
    if any(", " in key for key in result[0].keys()):
        return {"success": False, "message": "Keys can't contain ', '."}
    keys = [row.keys() for row in result]
    if len(set(keys)) != 1:
        return {"success": False, "message": "All rows must have the same keys."}
    data = ", ".join(result[0].keys())
    for row in result:
        data += "\n" + ", ".join(str(value) for value in row.values())
    return {"success": True, "data": data}