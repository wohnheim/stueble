def clean_single_data(data: dict):
    return {k: v if k != "data" else v[0] for k, v in data.items()}