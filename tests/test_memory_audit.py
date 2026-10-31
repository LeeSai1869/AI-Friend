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


def test_audit_distinguishes_retained_migration_and_reused_ids(tmp_path):
    for folder in ['Raw Memory','Tested Memory','entries']:(tmp_path/folder).mkdir()
    old='mem_Cod_0000000000005'
    legacy={'id':old,'domain_created':'Cod','memory_class':'raw','kind':'fact','content':'original'}
    (tmp_path/'entries'/f'{old}.json').write_text(json.dumps(legacy))
    migrated={**legacy,'id':'raw_original_abcdefgh','source':{'legacy_id':old}}
    (tmp_path/'Raw Memory'/'raw_original_abcdefgh.json').write_text(json.dumps(migrated))
    (tmp_path/'Tested Memory'/f'{old}.json').write_text(json.dumps({**legacy,'memory_class':'tested','content':'new checked fact'}))
    (tmp_path/'entries'/'_sequences.json').write_text('{"Cod":5}')
    result=audit(tmp_path)
    assert result['counts']=={'Cod/raw':1,'Cod/tested':1}
    assert result['exact_raw_duplicate_groups']==[]
    assert result['retained_legacy_copies']==[{'legacy_id':old,'canonical_id':'raw_original_abcdefgh'}]
    assert result['reused_legacy_ids']==[{'legacy_id':old,'raw_id':'raw_original_abcdefgh','canonical_class':'tested'}]
    assert result['errors']==[]
