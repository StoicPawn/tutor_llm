from __future__ import annotations

import streamlit as st

from studyforge.db import list_documents
from studyforge.research_lab_client import configured_client
from studyforge.teacher import summarize
from studyforge.workspaces import list_workspaces as list_tutor_workspaces

st.set_page_config(page_title='Research Lab', page_icon='🧪', layout='wide')
st.title('Research Lab')
st.caption(
    'Ambiente Python condiviso e opzionale. Tutor LLM ed Expert My Rules restano '
    'autonomi: collaborano soltanto quando usano lo stesso project_key.'
)

client = configured_client()
if client is None:
    st.warning('Research Lab non configurato. Imposta RESEARCH_LAB_URL e RESEARCH_LAB_TOKEN nel profilo server.')
    st.stop()

if client.health():
    st.success('Research Lab connesso')
else:
    st.error('Research Lab non raggiungibile')
    st.stop()

try:
    workspaces = client.workspaces()
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.subheader('Progetto sincrono')
c1, c2 = st.columns([2, 3])
project_key = c1.text_input(
    'Project key condiviso',
    value=st.session_state.get('lab_project_key', ''),
    help='Usa la stessa chiave in Tutor LLM ed Expert My Rules per lavorare sullo stesso workspace Lab.',
)
project_name = c2.text_input(
    'Nome progetto',
    value=st.session_state.get('lab_project_name', ''),
)
project_description = st.text_area(
    'Descrizione',
    value=st.session_state.get('lab_project_description', ''),
    height=80,
)
if st.button('Aggancia / crea progetto condiviso', disabled=not project_key or not project_name):
    try:
        ws = client.ensure_workspace(project_key, project_name, project_description)
        st.session_state.lab_workspace_id = ws['id']
        st.session_state.lab_project_key = project_key
        st.session_state.lab_project_name = project_name
        st.session_state.lab_project_description = project_description
        st.success(f"Progetto condiviso pronto: {ws['id']}")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))

if not workspaces:
    st.info('Crea o aggancia il primo progetto condiviso per iniziare.')
    st.stop()

labels = {
    f"{w['name']} · {(w.get('metadata') or {}).get('project_key', 'senza key')} · {w['id']}": w['id']
    for w in workspaces
}
default_index = 0
saved_id = st.session_state.get('lab_workspace_id')
if saved_id:
    values = list(labels.values())
    if saved_id in values:
        default_index = values.index(saved_id)

selected_label = st.selectbox('Workspace Lab', list(labels), index=default_index)
lab_workspace_id = labels[selected_label]
selected = next(w for w in workspaces if w['id'] == lab_workspace_id)
selected_meta = selected.get('metadata') or {}
active_project_key = str(selected_meta.get('project_key') or project_key or selected['name'])
st.session_state.lab_workspace_id = lab_workspace_id
st.session_state.lab_project_key = active_project_key

st.caption(
    f"{selected.get('run_count', 0)} run · "
    f"{selected.get('size_bytes', 0) / 1048576:.2f} MB · "
    f"project_key `{active_project_key}`"
)

st.divider()
st.subheader('Pubblica teoria da Tutor LLM')
st.caption(
    'Tutor legge i documenti nel proprio workspace, costruisce uno snapshot teorico '
    'con fonti e lo pubblica nel Lab. Expert My Rules può leggerlo con latest_context.'
)

tutor_workspaces = list_tutor_workspaces()
if tutor_workspaces:
    tutor_labels = {f"{w['name']} (#{w['id']})": int(w['id']) for w in tutor_workspaces}
    tutor_label = st.selectbox('Workspace Tutor', list(tutor_labels))
    tutor_workspace_id = tutor_labels[tutor_label]
    docs = list_documents(tutor_workspace_id)
    doc_labels = {f"{d['name']} (#{d['id']})": int(d['id']) for d in docs}
    selected_doc_labels = st.multiselect('Documenti da usare', list(doc_labels), default=list(doc_labels))
    document_ids = [doc_labels[x] for x in selected_doc_labels]
    theory_request = st.text_area(
        'Focus teorico',
        value=(
            'Estrai definizioni, ipotesi, risultati principali, dipendenze logiche, '
            'casi limite, possibili controesempi e punti che meritano verifica numerica.'
        ),
        height=110,
    )
    epistemic_mode = st.selectbox('Politica epistemica', ['Grounded', 'Tutor', 'Expert'], index=0)

    if st.button(
        'Genera snapshot teorico',
        disabled=not document_ids or not theory_request,
    ):
        try:
            with st.spinner('Tutor analizza i documenti...'):
                content, sources = summarize(
                    tutor_workspace_id,
                    theory_request,
                    document_ids,
                    epistemic_mode,
                )
            st.session_state.lab_theory_content = content
            st.session_state.lab_theory_sources = sources
            st.success('Snapshot generato. Verificalo e pubblicalo nel progetto condiviso.')
        except Exception as exc:
            st.error(str(exc))

    if st.session_state.get('lab_theory_content'):
        st.markdown(st.session_state.lab_theory_content)
        with st.expander('Fonti dello snapshot'):
            st.json(st.session_state.get('lab_theory_sources') or [])
        if st.button('Pubblica snapshot nel Lab', type='primary'):
            try:
                result = client.publish_context(
                    lab_workspace_id,
                    active_project_key,
                    st.session_state.lab_theory_content,
                    title='Tutor theory snapshot',
                    topic=theory_request,
                    sources=st.session_state.get('lab_theory_sources') or [],
                )
                st.success(f"Snapshot pubblicato come run {result['id']}")
            except Exception as exc:
                st.error(str(exc))
else:
    st.info('Nessun workspace Tutor disponibile.')

st.divider()
st.subheader('Esperimento Python manuale')
code = st.text_area(
    'Python',
    value="""import numpy as np

x = np.linspace(0, 1, 1000)
print('mean=', float(x.mean()))
""",
    height=280,
)
title = st.text_input('Titolo esperimento', value='Test teoria')
timeout = st.number_input('Timeout (secondi)', min_value=1, max_value=300, value=120)

if st.button('Esegui nel Research Lab'):
    try:
        with st.spinner('Esecuzione sul server...'):
            result = client.run(
                lab_workspace_id,
                code,
                title=title,
                timeout_seconds=int(timeout),
                metadata={'caller': 'tutor_llm', 'project_key': active_project_key},
            )
        if result.get('status') == 'success':
            st.success(f"Completato in {result.get('duration_seconds')} s")
        else:
            st.error(f"Run: {result.get('status')}")
        st.code(result.get('stdout') or '', language='text')
        if result.get('stderr'):
            st.code(result['stderr'], language='text')
        if result.get('artifacts'):
            st.json(result['artifacts'])
    except Exception as exc:
        st.error(str(exc))

st.divider()
st.subheader('Timeline condivisa')
try:
    runs = client.runs(lab_workspace_id)
    for run in runs:
        metadata = run.get('metadata') or {}
        kind = metadata.get('kind') or 'experiment'
        caller = metadata.get('caller') or 'unknown'
        with st.expander(f"{run['title']} · {kind} · {caller} · {run['status']}"):
            st.caption(f"{run.get('created_at', '')} · {run.get('duration_seconds', 0)} s · {run['id']}")
            if metadata.get('content'):
                st.markdown(str(metadata['content']))
            if metadata.get('sources'):
                with st.expander('Fonti / provenance'):
                    st.json(metadata['sources'])
            if run.get('stdout'):
                st.code(run['stdout'], language='text')
            if run.get('stderr'):
                st.code(run['stderr'], language='text')
            if run.get('artifacts'):
                st.json(run['artifacts'])
except Exception as exc:
    st.error(str(exc))

st.divider()
if st.button('Elimina questo workspace Lab'):
    if st.session_state.get('confirm_lab_delete'):
        try:
            client.delete_workspace(lab_workspace_id)
            st.session_state.confirm_lab_delete = False
            st.session_state.pop('lab_workspace_id', None)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    else:
        st.session_state.confirm_lab_delete = True
        st.warning('Premi di nuovo per confermare la cancellazione permanente di workspace e run.')
