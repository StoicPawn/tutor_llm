from __future__ import annotations
import streamlit as st
from studyforge.config import settings
from studyforge.inference import health
from studyforge.workspaces import ensure_default_workspace, list_workspaces, get_workspace
from studyforge.db import list_documents
from studyforge.sessions import start_session, active_sessions
from studyforge.notes import create_note
from studyforge.teacher import answer_question, deepen
from studyforge.interactive import start_exercise_session
from studyforge.repetition import schedule_concept
from studyforge.study_view import study_workspace_state, set_reading_context, selection_context, contextual_tutor_request

st.set_page_config(page_title='Tutor LLM · Studio', page_icon='📖', layout='wide')
ensure_default_workspace()
st.title('Studio')
st.caption('Documento · Tutor · Note nello stesso contesto di apprendimento')

workspaces=list_workspaces()
workspace_labels={f"{w['name']} (#{w['id']})":int(w['id']) for w in workspaces}
with st.sidebar:
    workspace_id=workspace_labels[st.selectbox('Workspace',list(workspace_labels))]
    workspace=get_workspace(workspace_id)
    epistemic_mode=st.radio('Modalità',['Grounded','Tutor','Expert'],index=1)
    if workspace and workspace['goal']: st.caption('Obiettivo: '+workspace['goal'])
    st.caption(f"Deploy: {settings.deploy_mode} · {settings.inference_provider} · {settings.chat_model}")
    st.success('Inference pronta') if health() else st.error('Inference non disponibile')

sessions=active_sessions(workspace_id,20)
if 'study_session_id' not in st.session_state or not any(int(s['id'])==int(st.session_state.study_session_id) for s in sessions):
    st.session_state.study_session_id=start_session(workspace_id,workspace['goal'] if workspace else '')
sid=int(st.session_state.study_session_id)

docs=list_documents(workspace_id)
if not docs:
    st.info('Carica prima almeno un documento dalla pagina principale Tutor LLM.')
    st.stop()
doc_labels={f"{d['name']} (#{d['id']})":int(d['id']) for d in docs}

current=study_workspace_state(workspace_id,sid)
default_doc=current.get('active_document_id')
default_label=next((k for k,v in doc_labels.items() if v==default_doc),list(doc_labels)[0])

bar1,bar2,bar3=st.columns([4,1.2,1.2])
with bar1:
    doc_label=st.selectbox('Documento',list(doc_labels),index=list(doc_labels).index(default_label))
    document_id=doc_labels[doc_label]
with bar2:
    page=st.number_input('Pagina',min_value=1,value=int(current.get('active_page') or 1),step=1)
with bar3:
    if st.button('Nuova sessione'):
        st.session_state.study_session_id=start_session(workspace_id,workspace['goal'] if workspace else '')
        st.rerun()

set_reading_context(sid,workspace_id,document_id,int(page))
state=study_workspace_state(workspace_id,sid,document_id,int(page))
page_data=state.get('page')

left,right=st.columns([1.35,1],gap='large')
with left:
    st.subheader('Documento')
    if not page_data:
        st.warning('Pagina non disponibile. Il documento potrebbe non avere pagine fisiche o la pagina richiesta non esiste.')
    else:
        st.caption(f"{page_data['document_name']} · p. {page_data['page']} · layout blocks {len(page_data['blocks'])} · OCR {'sì' if page_data['ocr_used'] else 'no'}")
        st.markdown('---')
        st.text_area('Testo pagina',value=page_data['text'],height=470,disabled=True,label_visibility='collapsed')

    st.markdown('### Selezione / passaggio')
    selection_text=st.text_area('Incolla o seleziona il passaggio su cui vuoi lavorare',value=st.session_state.get('study_selection',''),height=120,placeholder='Nel client iPad questo campo verrà popolato direttamente dalla selezione nel PDF.')
    st.session_state.study_selection=selection_text
    if selection_text and page_data:
        try:
            mapped=selection_context(workspace_id,document_id,int(page),selection_text)
            st.session_state.study_mapped_selection=mapped
            top=mapped.get('matches',[None])[0]
            if top: st.caption(f"Collegato a chunk {top['chunk_index']} · confidenza {top['score']:.0%} · {mapped['citation']}")
        except Exception as exc: st.warning(str(exc))

    actions=st.columns(6)
    labels=[('Spiegami','explain'),('Perché?','why'),('Approfondisci','deepen'),('Esempio','example'),('Esercizio','exercise'),('Prerequisiti','prerequisites')]
    chosen=None
    for col,(label,key) in zip(actions,labels):
        if col.button(label,use_container_width=True,disabled=not selection_text): chosen=key
    extra=st.text_input('Istruzione aggiuntiva',placeholder='Es. spiegalo intuitivamente prima della formalizzazione')
    if chosen:
        try:
            mapped=st.session_state.get('study_mapped_selection') or selection_context(workspace_id,document_id,int(page),selection_text)
            prompt=contextual_tutor_request(chosen,mapped,extra)
            if chosen=='deepen': content,sources=deepen(workspace_id,prompt,[document_id],epistemic_mode)
            elif chosen=='exercise':
                exercise_sid=start_exercise_session(workspace_id,selection_text,[document_id],4,epistemic_mode)
                st.session_state.exercise_session_id=exercise_sid
                content='Ho creato una sessione di esercizi mirata sul passaggio selezionato. Apri la pagina principale → Esercizi per svolgerla.'; sources=[]
            else: content,sources=answer_question(workspace_id,prompt,[document_id],epistemic_mode)
            st.session_state.study_tutor_content=content; st.session_state.study_tutor_sources=sources
            set_reading_context(sid,workspace_id,document_id,int(page),selection_text)
        except Exception as exc: st.error(str(exc))

with right:
    tutor_tab,notes_tab,plan_tab=st.tabs(['Tutor','Note','Oggi'])
    with tutor_tab:
        st.subheader('Tutor contestuale')
        q=st.text_area('Chiedi qualcosa',height=100,placeholder='Il tutor conosce workspace, documento e pagina correnti.')
        if st.button('Invia al Tutor',type='primary',disabled=not q):
            try:
                contextual=q
                if selection_text:
                    contextual += f"\n\nPASSAGGIO CHE STO LEGGENDO ({page_data['document_name'] if page_data else ''}, p.{page}):\n{selection_text}"
                content,sources=answer_question(workspace_id,contextual,[document_id],epistemic_mode)
                st.session_state.study_tutor_content=content; st.session_state.study_tutor_sources=sources
            except Exception as exc: st.error(str(exc))
        if st.session_state.get('study_tutor_content'):
            st.markdown(st.session_state.study_tutor_content)
            with st.expander('Fonti recuperate'): st.json(st.session_state.get('study_tutor_sources',[]))

    with notes_tab:
        st.subheader('Foglio di studio')
        note_title=st.text_input('Titolo',value=f"{page_data['document_name'] if page_data else 'Nota'} · p.{page}")
        note_body=st.text_area('Nota',height=300,placeholder='Scrivi appunti, passaggi, formule o idee. Su iPad questo spazio diventerà anche un foglio Apple Pencil.')
        if st.button('Salva nota',disabled=not note_title):
            create_note(workspace_id,note_title,note_body,document_id=document_id,page=int(page))
            st.success('Nota salvata nel workspace.')
        if selection_text and st.button('Aggiungi selezione alla nota'):
            st.session_state.note_seed=(st.session_state.get('note_seed','')+'\n'+selection_text).strip()
            st.info('Selezione memorizzata come seme per una nota; l’editor Pencil userà lo stesso legame documento/pagina.')

    with plan_tab:
        st.subheader('Next Best Activity')
        nxt=state.get('next_activity') or {}
        if nxt: st.info(f"**{nxt.get('title',nxt.get('type','Attività'))}**\n\n{nxt.get('reason','')}")
        else: st.write('Continua a studiare: il planner userà progressi e ripassi per proporti la prossima attività.')
        reviews=state.get('reviews') or []
        if reviews:
            st.markdown('**Coda ripassi**')
            for r in reviews[:8]: st.write(f"• {r.get('concept','')} · {r.get('due_at','')[:10] if r.get('due_at') else 'ora'}")
        weak=state.get('weakest') or []
        if weak:
            st.markdown('**Concetti deboli**')
            for r in weak[:5]: st.write(f"• {r['name']} · mastery {float(r['mastery']):.0%}")
        if selection_text and st.button('Metti questo concetto in ripasso'):
            concept=selection_text[:180]
            schedule_concept(workspace_id,concept)
            st.success('Aggiunto alla coda di ripasso.')
