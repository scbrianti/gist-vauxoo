def cr_execute(query, *parameters):
    """Get the database-dictionary-data from each field
    to validate and parser the type of data"""
    param_parsed = []
    for param in parameters:
        param_type_of_data = seudo_dict_of_data[param]
        if not isinstance(param, param_type_of_data):
            raise BaseException("I catched a SQL injection! Tontuelo")
        if issubclass(param_type_of_data, list):
            param = '(' + ','.join(map(str, param)) + ')'
        param_parsed.append(param)
    return query % tuple(param_parsed)


# Hard code the database-dictionary-data for example.
# This information is stored in database original cursor.
seudo_dict_of_data = {
    10: int,
    ';update injection..;': tuple,
    (1, 2, 3): tuple,
}

query = "SELECT amount, id FROM table WHERE amount=%d, id IN %s"

print "*" * 10, "Parameters in the correct way without sql injection"
parameters = (10, (1, 2, 3))
res = cr_execute(query, *parameters)
print "res: ", res
# Console Result:
# ********** Parameters in the correct way without sql injection
# res:  SELECT amount, id FROM table WHERE amount=10, id IN (1, 2, 3)

print "*" * 10, "Parameters in the bad way with sql injection"
parameters = (10, ';update injection..;',)
res = cr_execute(query % parameters)
print "res: ", res
# Console Result:
# ********** Parameters in the bad way with sql injection
# res:  SELECT amount, id FROM table WHERE amount=10, id IN ;update injection..;

print "*" * 10, "Parameters in the correct way with sql injection"
parameters = (10, ';update injection..;',)
res = cr_execute(query, *parameters)
print "res: ", res
# Console Result:
# ********** Parameters in the correct way with sql injection
# BaseException: I catched a SQL injection! Tontuelo
