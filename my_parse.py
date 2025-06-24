from sqlglot import parse_one, exp
from sqlglot.optimizer import normalize


def normalize_aliases(expression: exp.Expression) -> exp.Expression:
    for node in expression.walk():
        if isinstance(node, exp.Column):
            node.set("table", None)  # remove table alias
    return expression


def extract_all_subqueries(expr):
    """
    Recursively find all subqueries inside expr, at any depth.
    Returns a list of all subqueries (exp.Subquery or exp.Select nodes).
    """
    subqueries = []

    def recurse(node):
        # If this node is a subquery or select, add it
        if isinstance(node, (exp.Subquery, exp.Select)):
            subqueries.append(node)
        # Then recurse all child expressions
        for child in node.args.values():
            if isinstance(child, exp.Expression):
                recurse(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, exp.Expression):
                        recurse(item)

    recurse(expr)
    return subqueries


def where_predicates(query):
    def recurse(expr, results, depth):
        if isinstance(expr, exp.And):
            op = "AND"
            left_expr = expr.args["this"]
            right_expr = expr.args["expression"]
            results.append(
                (
                    op,
                    normalize_aliases(left_expr).sql(),
                    normalize_aliases(right_expr).sql(),
                )
            )
            recurse(left_expr, results, depth + 1)
            recurse(right_expr, results, depth + 1)
            depth -= 1

        elif isinstance(expr, exp.Or):
            op = "OR"
            left_expr = expr.args["this"]
            right_expr = expr.args["expression"]
            results.append(
                (
                    op,
                    normalize_aliases(left_expr).sql(),
                    normalize_aliases(right_expr).sql(),
                )
            )
            recurse(left_expr, results, depth + 1)
            recurse(right_expr, results, depth + 1)

        elif isinstance(expr, exp.Not):
            op = "NOT"
            inner = expr.args["this"]
            results.append((op, normalize_aliases(inner).sql(), None))
            recurse(inner, results, depth + 1)
        elif depth == 0:
            # If we reach here, it means we have a base case (not an AND, OR, or NOT)
            results.append((None, expr.sql(), None))

    results = []
    subqueries = extract_all_subqueries(query)
    for q in subqueries:
        where = q.args.get("where")
        if where:
            recurse(where.this, results, 0)
    return set(results)


def columns(query: exp.Expression):
    for select in query.find_all(exp.Select):
        for column in select.find_all(exp.Column):
            print(column.sql())


def extract_select_columns(expression: exp.Expression):
    """
    Recursively extract all distinct column names in SELECT expressions
    from the SQL query and its subqueries.
    """
    columns = set()
    for select in expression.find_all(exp.Select):
        for column in select.find_all(exp.Column):
            columns.update(extract_columns_from_expression(select))

    return columns


def extract_columns_from_expression(expr: exp.Expression):
    """
    Extract all column references from a given SQL expression.
    """
    return {col.name for col in expr.find_all(exp.Column)}


def extract_tables(expression: exp.Expression):
    tables = set()

    # Handle regular tables in FROM and JOIN
    for table in expression.find_all(exp.Table):
        tables.add(table.name)

    # Handle subqueries (e.g., FROM (SELECT ...))
    for subquery in expression.find_all(exp.Subquery):
        tables.update(extract_tables(subquery.this))

    # Handle CTEs: WITH cte AS (...)
    with_clause = expression.args.get("with")
    if with_clause:
        for cte in with_clause.expressions:
            tables.update(extract_tables(cte.this))

    # Handle UNION, INTERSECT, EXCEPT
    for set_expr in expression.find_all(exp.SetOperation):
        if set_expr.left:
            tables.update(extract_tables(set_expr.left))
        if set_expr.right:
            tables.update(extract_tables(set_expr.right))

    return tables


def extract_aggregates(expression: exp.Expression):
    aggregates = set()

    # 1. Get GROUP BY columns (if any)
    group_by_clause = expression.args.get("group")
    group_by_cols = []
    if group_by_clause:
        for g in group_by_clause.expressions:
            normal_g = normalize_aliases(g)
            if normal_g is not None:
                normal_g = normal_g.sql()
            if isinstance(g, exp.Column):
                group_by_cols.append(normal_g)
            else:
                group_by_cols.append(normal_g)  # supports expressions like DATE(ts)

    # 2. Find aggregates in the current expression
    for agg in expression.find_all(exp.AggFunc):
        func_name = agg.__class__.__name__.upper()
        arg_expr = agg.args.get("this")
        arg_expr = normalize_aliases(arg_expr)
        arg_expr = normalize_aliases(arg_expr)
        if arg_expr is not None:
            arg_expr = arg_expr.sql()
        if arg_expr:
            aggregates.add((func_name, arg_expr, tuple(group_by_cols)))

    # 3. Recurse into subqueries
    for subquery in expression.find_all(exp.Subquery):
        aggregates.update(extract_aggregates(subquery.this))

    # 4. Recurse into WITH clause
    with_clause = expression.args.get("with")
    if with_clause:
        for cte in with_clause.expressions:
            aggregates.update(extract_aggregates(cte.this))

    # 5. Recurse into set operations
    for set_expr in expression.find_all(exp.SetOperation):
        if set_expr.left:
            aggregates.update(extract_aggregates(set_expr.left))
        if set_expr.right:
            aggregates.update(extract_aggregates(set_expr.right))

    return aggregates

def extract_functions(expression: exp.Expression):
    functions = set()

    # Traverse all nodes in the AST
    for node in expression.walk():
        if isinstance(node, exp.Func):
            # exp.Func is base class; actual class gives function name
            func_name = node.__class__.__name__.upper()
            functions.add(node.sql_name().upper())
        elif isinstance(node, exp.Anonymous):
            # User-defined or unclassified function
            functions.add(node.name.upper())

    return functions



def extract_functions_recursive(expression: exp.Expression):
    funcs = extract_functions(expression)

    for subquery in expression.find_all(exp.Subquery):
        funcs.update(extract_functions_recursive(subquery.this))

    with_clause = expression.args.get("with")
    if with_clause:
        for cte in with_clause.expressions:
            funcs.update(extract_functions_recursive(cte.this))

    for set_expr in expression.find_all(exp.SetOperation):
        if set_expr.left:
            funcs.update(extract_functions_recursive(set_expr.left))
        if set_expr.right:
            funcs.update(extract_functions_recursive(set_expr.right))

    return funcs



sql = """
SELECT e.name, AVG(s.amount)
FROM employees e
JOIN departments d ON e.dept_id = d.id
JOIN salaries s ON e.id = s.emp_id
WHERE s.amount > 50000
AND NOT EXISTS (
    SELECT * FROM bonuses b WHERE b.emp_id = e.id
)
GROUP BY e.name
"""

def jaccard_similarity(set1, set2):
    if not set1 and not set2:
        return 1.0  # deux ensembles vides sont considérés identiques
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union != 0 else 0




# Example usage:
# sql = """
# SELECT a, b FROM (
#     SELECT c, d FROM my_table WHERE e > 5
# ) AS subquery WHERE b < 10
# """
