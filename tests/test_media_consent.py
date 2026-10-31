from types import SimpleNamespace
import pytest
from section_1_central_mind.mind.consent import ConsentRequests
from section_8_tools.web.media import BrowserMedia


def request(store):
    return store.offer(description='Read screenshot?', tool='browser_media',
                       args={'url':'https://example.org', 'allowed_origins':['https://example.org'], 'mode':'image'})


def test_human_approval_is_required_and_single_use(tmp_path):
    store=ConsentRequests()
    row=request(store)
    tool=BrowserMedia(tmp_path, SimpleNamespace(consent_requests=store))
    with pytest.raises(PermissionError):
        tool.effects({'request_id':row['request_id'], 'approved':True})
    store.decide(row['request_id'],True)
    assert tool.effects({'request_id':row['request_id']})[0].target=='https://example.org'
    assert tool.approved({'request_id':row['request_id']},consume=True)['mode']=='image'
    with pytest.raises(PermissionError):
        tool.effects({'request_id':row['request_id']})


def test_denial_expiry_cross_session_and_malformed_approval(tmp_path):
    one,two=ConsentRequests(),ConsentRequests()
    row=request(one)
    with pytest.raises(PermissionError):
        two.decide(row['request_id'],True)
    with pytest.raises(ValueError):
        one.decide(row['request_id'],'yes')
    one.decide(row['request_id'],False)
    with pytest.raises(PermissionError):
        one.approved(row['request_id'],'browser_media')
    other=request(one)
    one._rows[other['request_id']]['expires_at']=0
    with pytest.raises(PermissionError):
        one.decide(other['request_id'],True)


def test_permission_does_not_override_url_exclusion(tmp_path,monkeypatch):
    policy=tmp_path/'policy.json'
    policy.write_text('{"version":1,"blocked":["example.org"]}')
    monkeypatch.setenv('AI_FRIEND_URL_POLICY',str(policy))
    store=ConsentRequests();row=request(store);store.decide(row['request_id'],True)
    with pytest.raises(PermissionError):
        BrowserMedia(tmp_path,SimpleNamespace(consent_requests=store)).effects({'request_id':row['request_id']})


def test_media_bytes_are_not_written_to_broker_history_or_log():
    import time
    from section_1_central_mind.mind.broker import ToolBroker
    logs=[]
    broker=SimpleNamespace(history=[], logger=logs.append, call_count=1)
    args={'data_base64':'private-image-bytes','name':'frame.png'}
    ToolBroker._finish(broker,'document_read',args,time.time(),True,{},None)
    assert 'private-image-bytes' not in str(broker.history)+str(logs)
    assert args['data_base64']=='private-image-bytes'
