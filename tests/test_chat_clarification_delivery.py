from types import SimpleNamespace

from section_4_chatbox.runtime import ChatRuntime


def test_clarification_is_delivered_and_preserved_for_the_next_turn(tmp_path):
    packets = []
    def process(text, context):
        packets.append(context)
        return {'status': 'needs_answers', 'questions': [{'attribute': 'version', 'question': 'Which API version should I target?'}]}
    chat = ChatRuntime(SimpleNamespace(process=process), tmp_path)
    result = chat.respond('Build the API client')
    assert result['ok'] and result['status'] == 'needs_answers'
    assert result['text'] == 'Which API version should I target?'
    history = chat.load_chat(result['chat_id'])['turns']
    assert history[-1]['action'] == 'question'
    assert history[-1]['text'] == result['text']
    chat.respond('Version 2', chat_id=result['chat_id'])
    assert 'Which API version' in str(packets[-1]['chat'])


def test_execution_errors_are_not_presented_as_success(tmp_path):
    runtime = ChatRuntime(SimpleNamespace(process=lambda *args, **kwargs: {'status': 'error', 'errors': ['guard denied']}), tmp_path)
    result = runtime.respond('task')
    assert not result['ok'] and result['error'] == 'guard denied'
