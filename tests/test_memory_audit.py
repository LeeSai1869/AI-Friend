import json
from scripts.memory_audit import audit


def test_audit_lists_old_duplicates_without_rewriting_or_exposing_content(tmp_path):
    folder=tmp_path/'Raw Memory';folder.mkdir()
    for index in range(2):
        (folder/f'{index}.json').write_text(json.dumps({'id':str(index),'domain_created':'Cod','memory_class':'raw','kind':'fact','content':'private lesson'}))
    before={path.name:path.read_bytes() for path in folder.iterdir()}
    result=audit(tmp_path)
    assert result['exact_raw_duplicate_groups']==[['0','1']]
    assert result['writes_performed'] is False
    assert 'private lesson' not in json.dumps(result)
    assert before=={path.name:path.read_bytes() for path in folder.iterdir()}
