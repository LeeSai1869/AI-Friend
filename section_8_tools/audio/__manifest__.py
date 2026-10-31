ORGAN = {
    'name':'audio', 'kind':'tool', 'scope':'outside_guards',
    'capabilities':['audio_transcribe'],
    'security':{'requires':{'audio_transcribe':['workspace.read','process.execute']}},
    'keywords':[], 'entry_module':'audio.audio', 'entry_attr':'TOOLS',
}
