from section_3_memory.api import Memory
from section_3_memory.bridge import MemoryBridge


def test_natural_question_retrieves_relevant_raw_content_past_old_preview(tmp_path):
    memory=Memory(tmp_path)
    entry=memory.record(domain='Cod',kind='fact',title='Dictionary counting',content='Intro. '*100+'Words are counted in nested string values.',memory_class='raw')
    rows=MemoryBridge(memory).recall('How do I count dictionary words?')
    assert rows[0]['id']==entry.id
    assert 'nested string values' in rows[0]['content']
    assert rows[0]['memory_class']=='raw' and not rows[0]['content_truncated']


def test_long_retrieval_marks_truncation_without_altering_source(tmp_path):
    memory=Memory(tmp_path)
    entry=memory.record(domain='Cod',kind='fact',title='Large source',content='data '*4000,memory_class='raw')
    row=MemoryBridge(memory).recall('Large source')[0]
    assert row['content_truncated'] and row['content_chars']==20000
    assert len(memory.get(entry.id).content)==20000


def test_other_session_append_is_visible_after_index_was_built(tmp_path):
    first,second=Memory(tmp_path),Memory(tmp_path)
    assert first.search(memory_class='tested')==[]
    entry=second.record(domain='Cod',kind='fact',title='New knowledge',content='A newly verified observation',memory_class='tested')
    assert first.search(memory_class='tested')[0].id==entry.id


def test_raw_cannot_crowd_domain_knowledge_out_of_recall(tmp_path):
    from section_3_memory.service import MemoryService
    memory=Memory(tmp_path)
    for index in range(5):
        memory.record(domain='Cod',kind='fact',title='counter',content=f'counter raw {index}',memory_class='raw')
    tested=memory.record(domain='Cod',kind='fact',title='counter',content='counter verified',memory_class='tested')
    client=MemoryService(memory).client(actor='coder',role='domain',domain='Cod')
    rows=client.recall('counter',limit=1)
    assert [row['id'] for row in rows]==[tested.id]
    assert client.recall('counter',memory_class='raw')==[]


def test_reasoner_bounds_combined_source_context_and_marks_every_cut():
    from types import SimpleNamespace
    from section_1_central_mind.mind.reasoner.head import Reasoner
    rows=[{'id':str(index),'memory_class':'raw','content':'x'*12000,'content_chars':20000,'content_truncated':True} for index in range(8)]
    recalled=Reasoner(memory=SimpleNamespace(recall=lambda **kwargs: rows))._recall('query')
    assert sum(len(row['content']) for row in recalled)==24000
    assert all(row['content_chars']==20000 and row['content_truncated'] for row in recalled)
    assert all('context_limit_reason' in row for row in recalled)
