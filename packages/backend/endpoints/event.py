
import json

from flask import Blueprint, Response, request
from psycopg import sql

from backend.database import database as db

event = Blueprint("event", __name__)

@event.route("", methods=["GET"])
def get_events():
    """
    Get the events in the dorm.
    """

    name = request.args.get("name", None)

    columns = [
        "name", 
        "category", 
        "location", 
        "start_time", 
        "end_time", 
        "full_days", 
        "description", 
        "image"
    ]

    query = sql.SQL("SELECT {columns} \
                    FROM events.events \
                    WHERE (start_time >= CURRENT_DATE) OR (end_time IS NOT NULL AND end_time >= NOW()) \
                    {name} \
                    ORDER BY start_time ASC").format(
        columns=sql.SQL(", ").join([sql.Identifier(col) for col in columns]),
        name=sql.SQL("AND name = {name}").format(name=sql.Placeholder()) if name else sql.SQL("")
        )
    
    result = db.custom_call(
        query=query,
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER,
        variables=[name] if name else []
    )

    if result.is_error:
        return Response(
            response=json.dumps({"code": 500, "message": str(result.error)}),
            status=500,
            mimetype="application/json"
        )

    data = [{key: value for key, value in zip(columns, i)} for i in result.data]
    # TODO: test time format conversion
    for i in data:
        if i["full_days"] is True:
            i["start"] = i["start_time"].strftime("%Y-%m-%d")
            i["end"] = i["end_time"].strftime("%Y-%m-%d") if i["end_time"] is not None else None
        else:
            i["start"] = i["start_time"].isoformat()
            i["end"] = i["end_time"].isoformat() if i["end_time"] is not None else None
        del i["full_days"]
        del i["start_time"]
        del i["end_time"]

    return Response(
        response=json.dumps(data),
        status=200,
        mimetype="application/json"
    )