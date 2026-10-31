import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from section_3_memory.api import Memory
from section_3_memory.service import MemoryService
from section_1_central_mind.mind.loop import CentralMind
from section_1_central_mind.mind.resource_socket import ResourceSocket
from section_5_domains.coding.coding_engine import CodingOrgan


CODE='def count_entries(entries: list[str]) -> int:\n    return len(entries)\n'


def stack(root):
    memory=Memory(root=root)
    service=MemoryService(memory)
    mind=CentralMind.__new__(CentralMind)
    organ=CodingOrgan()
    info=SimpleNamespace(name='coder',kind='domain',capabilities=[],manifest={
        'memory_domain':'Cod','intake_processing':{'mode':'automatic','capability':'examine_intake'}})
    language=SimpleNamespace(name='languages',kind='domain',capabilities=[],manifest={
        'memory_domain':'Lng','intake_processing':{'mode':'deferred','reason':'Gradual communication and Trainer feedback'}})
    infos=[info,language]
    mind.inventory=SimpleNamespace(all=lambda:infos,get=lambda name:next((row for row in infos if row.name==name),None))
    mind._load_organ=lambda _:organ
    mind.broker=SimpleNamespace(bind_component=lambda _:object())
    mind.caller=object()
    mind._domain_brokers={}
    mind.memory_service=service
    mind.memory=service.client(actor='central_mind',role='central_mind',domain='Mind')
    service.register_proposal_handler(mind._receive_memory_proposal)
    mind.resource_socket=ResourceSocket()
    mind.resource_socket.connect('domain',mind._fulfill_domain_requirement)
    trainer=service.client(actor='trainer-user',role='trainer',domain='Cod')
    return mind,trainer,memory,organ


def intake(trainer,content=CODE,*,domain='Cod',filename='counter.py'):
    return trainer.record_trainer_intake(domain=domain,kind='fact',title='Source',content=content,
        source_refs=[filename],source={'source_path':filename,'source_kind':'file','sha256':hashlib.sha256(content.encode()).hexdigest()})


def test_raw_intake_is_queued_and_mind_alone_commits_scoped_tested_knowledge(tmp_path):
    mind,trainer,memory,organ=stack(tmp_path)
    raw_id=intake(trainer)
    raw_path=memory.store._find_path(raw_id)
    original=raw_path.read_bytes()
    assert mind.memory_service.processing.status(raw_id)['state']=='queued'
    result=mind.process_raw_intake(raw_id)
    assert result['storage']=='stored' and result['processing']=='completed'
    assert result['verification']=='passed' and result['decision']=='accepted'
    assert result['analysis']['declared_source_hash_matches'] is True
    assert result['analysis']['origin_authenticity']=='not_independently_verified'
    assert raw_path.read_bytes()==original
    entry=memory.get(result['knowledge_ids'][0])
    assert entry.memory_class=='tested' and entry.source_refs==[raw_id]
    payload=json.loads(entry.content)
    assert payload['kind']=='python_structure'
    assert 'behavior unverified' in payload['verification_scope']
    assert payload['payload']['functions'][0]['name']=='count_entries'
    assert entry.source['memory_proposal']['approved_by']=='central_mind'
    domain=mind.memory_service.client(actor='coder',role='domain',domain='Cod')
    assert domain.get(raw_id) is None and not hasattr(domain,'commit_approved_proposal')
    with pytest.raises(PermissionError):
        domain.record_trainer_intake(kind='fact',title='fake',content='fake')


def test_repeat_processing_and_duplicate_sources_do_not_duplicate_knowledge(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    one=intake(trainer)
    first=mind.process_raw_intake(one)
    assert mind.process_raw_intake(one)==first
    again=mind.process_raw_intake(one,retry=True)
    assert again['decision']=='duplicate' and again['knowledge_ids']==first['knowledge_ids']
    two=intake(trainer)
    assert two==one  # repeated intake reuses the immutable Raw source
    result=mind.process_raw_intake(two,retry=True)
    assert result['decision']=='duplicate'
    assert len(mind.memory_service.processing.intake_receipts(one))==2
    assert len([entry for entry in memory.store.iter_entries() if entry.memory_class=='tested'])==1
    assert [row['state'] for row in mind.memory_service.processing.history(one)]==['queued','examining','completed','examining','completed','examining','completed']


def test_conflicting_observations_are_deferred_without_overwriting_prior_knowledge(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    first=mind.process_raw_intake(intake(trainer))
    original=memory.store._find_path(first['knowledge_ids'][0]).read_bytes()
    second=mind.process_raw_intake(intake(trainer,'def other():\n    return 0\n'))
    assert second['decision']=='deferred'
    assert second['decisions'][0]['comparison']['status']=='conflicting'
    assert memory.store._find_path(first['knowledge_ids'][0]).read_bytes()==original
    assert len([entry for entry in memory.store.iter_entries() if entry.memory_class=='tested'])==1


def test_bad_syntax_is_a_failed_check_not_a_failed_storage_or_deleted_source(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    raw_id=intake(trainer,'def broken(:\n    pass\n')
    result=mind.process_raw_intake(raw_id)
    assert result['processing']=='completed' and result['verification']=='failed'
    assert result['decision']=='deferred' and result['knowledge_ids']==[]
    assert memory.get(raw_id).content.startswith('def broken(')


def test_language_sources_are_deferred_and_no_raw_code_is_executed(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    language=mind.process_raw_intake(intake(trainer,'suboh bakhair',domain='Lng',filename='phrases.txt'))
    assert language['processing']=='deferred' and language['verification']=='not_attempted'
    assert 'Trainer feedback' in language['reason']
    marker=tmp_path/'must-not-exist'
    code=f'from pathlib import Path\nPath({str(marker)!r}).write_text("executed")\n'
    result=mind.process_raw_intake(intake(trainer,code))
    assert result['verification']=='passed' and not marker.exists()


def test_restart_recovers_queue_and_writer_sequences_across_service_instances(tmp_path):
    first,trainer,memory,_=stack(tmp_path)
    second,_,_,_=stack(tmp_path)
    raw_id=intake(trainer)
    assert second.memory_service.processing.status(raw_id)['state']=='queued'
    result=second.process_pending_raw_intakes()[0]
    assert result['decision']=='accepted'
    # The first instance has an older sequence cache; it must not overwrite the new entry.
    extra=memory.record(domain='Cod',kind='fact',title='Other fact',content='Other',memory_class='tested')
    assert extra.id!=result['knowledge_ids'][0]
    assert memory.get(result['knowledge_ids'][0])


def test_resume_after_commit_then_processing_failure_reuses_existing_knowledge(tmp_path,monkeypatch):
    mind,trainer,memory,_=stack(tmp_path)
    raw_id=intake(trainer)
    finish=mind.memory_service.processing.finish
    seen=[]
    def interrupted(*args,**kwargs):
        if kwargs['state']=='completed' and not seen:
            seen.append(True)
            raise RuntimeError('Simulated interruption after memory commit')
        return finish(*args,**kwargs)
    monkeypatch.setattr(mind.memory_service.processing,'finish',interrupted)
    assert mind.process_raw_intake(raw_id)['processing']=='failed'
    restored,_,_,_=stack(tmp_path)
    result=restored.process_raw_intake(raw_id,retry=True)
    assert result['decision']=='duplicate'
    assert len([entry for entry in memory.store.iter_entries() if entry.memory_class=='tested'])==1


def test_processing_lease_excludes_other_workers_and_recovers_interruption(tmp_path):
    from section_3_memory.processing import ProcessingJournal
    one, two = ProcessingJournal(tmp_path), ProcessingJournal(tmp_path)
    one.enqueue('raw-one', 'Cod', 'digest')
    token = one.claim('raw-one', seconds=-1)
    replacement = two.claim('raw-one')
    assert replacement and replacement != token
    assert one.claim('raw-one') is None
    with pytest.raises(RuntimeError, match='lease was lost'):
        one.finish('raw-one', token, state='completed', payload={})
    two.finish('raw-one', replacement, state='completed', payload={'decision':'accepted'})
    assert one.claim('raw-one') is None
    assert [row['state'] for row in one.history('raw-one')] == [
        'queued', 'examining', 'processing_failed', 'examining', 'completed']


def test_concurrent_writers_never_reuse_entry_ids(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    memories = [Memory(root=tmp_path) for _ in range(8)]
    def write(pair):
        index, memory = pair
        return memory.record(domain='Cod',kind='fact',title=str(index),content=str(index),memory_class='tested').id
    with ThreadPoolExecutor(max_workers=8) as workers:
        ids = list(workers.map(write, enumerate(memories)))
    assert len(set(ids)) == 8
    assert len(list(memories[0].store.iter_entries())) == 8


def test_concurrent_duplicate_intake_keeps_one_raw_and_both_receipts(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    one,trainer,memory,_=stack(tmp_path)
    two,other,_,_=stack(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as workers:
        ids=list(workers.map(intake,[trainer,other]))
    assert ids[0]==ids[1]
    assert len([entry for entry in memory.store.iter_entries() if entry.memory_class=='raw'])==1
    receipts=one.memory_service.processing.intake_receipts(ids[0])
    assert len(receipts)==2 and sum(row['duplicate'] for row in receipts)==1


def test_same_text_in_different_domains_is_not_conflated(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    one=intake(trainer,'hello',domain='Cod')
    two=intake(trainer,'hello',domain='Lng')
    assert one!=two


def test_same_source_with_new_trainer_notes_reuses_raw_but_preserves_receipts(tmp_path):
    mind,trainer,memory,_=stack(tmp_path)
    def submit(note):
        context=[f'Q: Purpose?\nA: {note}']
        return trainer.record_trainer_intake(domain='Cod',kind='fact',title='lesson',
            content=CODE+'\n\nTrainer-provided intake context (not independently verified):\n'+'\n\n'.join(context),
            source={'trainer_context':context})
    one=submit('First note')
    original=memory.store._find_path(one).read_bytes()
    two=submit('Additional note')
    assert one==two and memory.store._find_path(one).read_bytes()==original
    assert 'Additional note' in str(mind.memory_service.processing.intake_receipts(one))
