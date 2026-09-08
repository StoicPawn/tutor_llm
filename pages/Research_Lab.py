from __future__ import annotations

import streamlit as st

from studyforge.research_lab_client import configured_client

st.set_page_config(page_title='Research Lab', page_icon='🧪', layout='wide')
st.title('Research Lab')
st.caption('Esperimenti Python in workspace separati. I dati del Lab non vengono mescolati con i workspace didattici di Tutor LLM.')

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

with st.expander('Nuovo workspace Lab'):
    name = st.text_input('Nome workspace', key='lab_ws_name')
    description = st.text_area('Descrizione', key='lab_ws_description')
    if st.button('Crea workspace Lab', disabled=not name):
        try:
            client.create_workspace(name, description, source_project='tutor_llm')
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

if not workspaces:
    st.info('Crea il primo workspace per iniziare.')
    st.stop()

labels = {f"{w['name']} · {w['id']}": w['id'] for w in workspaces}
selected_label = st.selectbox('Workspace Lab', list(labels))
lab_workspace_id = labels[selected_label]
selected = next(w for w in workspaces if w['id'] == lab_workspace_id)
st.caption(f"{selected.get('run_count', 0)} run · {selected.get('size_bytes', 0) / 1048576:.2f} MB")

code = st.text_area(
    'Python',
    value="""import numpy as np\n\nx = np.linspace(0, 1, 1000)\nprint('mean=', float(x.mean()))\n""",
    height=320,
)
title = st.text_input('Titolo esperimento', value='Test teoria')
timeout = st.number_input('Timeout (secondi)', min_value=1, max_value=300, value=120)

if st.button('Esegui nel Research Lab', type='primary'):
    try:
        with st.spinner('Esecuzione sul server...'):
            result = client.run(lab_workspace_id, code, title=title, timeout_seconds=int(timeout), metadata={'caller': 'tutor_llm'})
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
st.subheader('Storico run')
try:
    for run in client.runs(lab_workspace_id):
        with st.expander(f"{run['title']} · {run['status']} · {run['id']}"):
            st.caption(f"{run.get('duration_seconds', 0)} s · {run.get('created_at', '')}")
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
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    else:
        st.session_state.confirm_lab_delete = True
        st.warning('Premi di nuovo per confermare la cancellazione permanente di workspace e run.')
