from ortools.linear_solver import pywraplp
from psycopg import sql

from backend.database import database as db
from backend.datatypes.funcres import FuncRes, Message, Status


def map_applications():
    """
    Map applications to their respective categories and subcategories.
    """
    
    result = db.select(
        table="stueble.applications",
        columns=["id", "uuid", "motto", "description", "image", "date_of_time", "application_priority", "application_group", "created_at"],
        type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
    )

    if result.is_error:
        return FuncRes(
            error=str(result.error),
            status=Status.FULL_ERROR,
            message=Message(name="Map Applications Error",
                            type="error",
                            category="Map Applications",
                            code=500)
        )
    
    applications = result.data

    applications_sorted = dict()

    for applic in applications:
        applic_group = applic["application_group"]
        if applic_group not in applications_sorted:
            applications_sorted[applic_group] = []
        applications_sorted[applic_group].append({key: value for key, value in applic.items() if key != "application_group"})

    # clean the priorities, since through deletion of applications gaps can occurr
    for group in applications_sorted:
        applications_sorted[group] = sorted(applications_sorted[group], key=lambda x: x["application_priority"])
        for i, applic in enumerate(applications_sorted[group]):
            applic["application_priority"] = i + 1
    
    flat_applications = []
    for index, applic in enumerate(applications):
            a =  {
                "index": index,
                "priority": applic["application_priority"],
                "timestamp": applic["created_at"],
                "date": applic["date_of_time"],
                "group": applic_group,
                "id": applic["id"]
            }
            flat_applications.append(a)
    
    groups = sorted(set(applic["group"] for applic in flat_applications))
    dates = sorted(set(applic["date"] for applic in flat_applications))
    group_to_indices = {g: [applic["index"] for applic in flat_applications if applic["group"] == g] for g in groups}
    date_to_indices = {d: [applic["index"] for applic in flat_applications if applic["date"] == d] for d in dates}

    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return FuncRes(
            error="Could not create solver",
            status=Status.FULL_ERROR,
            message=Message(name="Map Applications Error",
                            type="error",
                            category="Map Applications",
                            code=500)
        )
    
    x = []
    for i in flat_applications:
        x.append(solver.BoolVar(f'x_{i["index"]}'))

    for d in dates:
        solver.Add(solver.Sum([x[i] for i in date_to_indices[d]]) == 1)

    # c_g = sum of x[i] where group == g
    c = []
    for g in groups:
        c_g = solver.IntVar(0, len(dates), f"c_{g}")
        solver.Add(c_g == solver.Sum([x[i] for i in group_to_indices[g]]))
        c.append(c_g)

    max_c = solver.IntVar(0, len(dates), "max_c")
    min_c = solver.IntVar(0, len(dates), "min_c")
    for c_g in c:
        solver.Add(max_c >= c_g)
        solver.Add(min_c <= c_g)

    # Hierarchical objective: balance first, then priorities
    BIG = len(dates) * 100000   # Must be much larger than sum(priorities) range
    solver.Minimize(BIG * (max_c - min_c) + solver.Sum(flat_applications[i]["priority"] * x[i] for i in range(len(flat_applications))))

    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        mapping_result = []
        for i, var in enumerate(x):
            if var.solution_value() > 0.5:
                app = flat_applications[i]
                mapping_result.append({
                    "id": app["id"],
                    "priority": app["priority"],
                    "group": app["group"],
                    "date": app["date"],
                    "created_at": app["timestamp"],
                })

        db_data = [i["id"] for i in mapping_result]
        for i in db_data:
            result = db.insert(
                table="stueble.dates",
                values={"application_id": i}
            )
            if result.is_error:
                pass
        
        query = sql.SQL("SELECT a.uuid, a.date_of_time FROM stueble.applications a INNER JOIN stueble.dates d ON a.id = d.application_id").format()
        result = db.custom_call(
            query=query,
            type_of_answer=db.ANSWER_TYPE.LIST_ANSWER
        )
        if result.is_error:
            return FuncRes(
                error=str(result.error),
                status=Status.FULL_ERROR,
                message=Message(name="Map Applications Error",
                                type="error",
                                category="Map Applications",
                                code=500)
            )
        
        data = {entry[1]: entry[0] for entry in result.data}

        return FuncRes(
            data=data,
            status=Status.FULL_SUCCESS,
            message=Message(name="Map Applications Success",
                            type="success",
                            category="Map Applications",
                            code=200)
        )
    else:
        return FuncRes(
            error="No optimal solution found",
            status=Status.FULL_ERROR,
            message=Message(name="Map Applications Error",
                            type="error",
                            category="Map Applications",
                            code=500)
        )