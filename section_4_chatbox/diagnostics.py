"""Compact diagnostics keep action steps visible without embedding Raw sources."""


def bounded(value, depth=0):
    if depth>5:return '[nested data omitted]'
    if isinstance(value,str):return value[:2000]
    if isinstance(value,list):return [bounded(item,depth+1) for item in value[:64]]
    if isinstance(value,dict):return {str(key):bounded(item,depth+1) for key,item in list(value.items())[:64]}
    return value


def plan_summary(plan):
    if not isinstance(plan,dict):return {}
    result={key:bounded(value) for key,value in plan.items() if key!='recalled_memory'}
    result['diagnostic_limits']={'max_string_chars':2000,'max_list_items':64, 'max_depth':5,
                                 'steps_total':len(plan.get('steps') or [])}
    result['recalled_memory']=[{key:row.get(key) for key in ['id','memory_class','domain','kind','content_chars','content_truncated','content_offset']}
                              for row in (plan.get('recalled_memory') or [])[:32] if isinstance(row,dict)]
    return result


def execution_summary(result):
    outcome=result.get('outcome') or {}
    rows=[]
    for receipt in outcome.get('receipts',[]):
        data=((receipt.get('functional_tests') or {}).get('data') or {})
        rows.append({'component':receipt.get('component'),'capability':receipt.get('capability'),
                     'status':receipt.get('status'),'operation':receipt.get('operation'),
                     'tests':{key:data.get(key) for key in ['tests_run','passed','failures','errors','returncode']}})
    return {'execution':outcome.get('execution',{}).get('status'),
            'verification':outcome.get('verification',{}).get('status'),'receipts':rows}
