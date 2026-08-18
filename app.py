from __future__ import annotations
import json, os, tempfile
import streamlit as st
from studyforge.config import settings
from studyforge.db import list_documents, save_lesson, delete_document, recent_lessons, get_document_page
from studyforge.ollama_client import health
from studyforge.pipeline import ingest_file
from studyforge.teacher import build_lesson, build_quiz, answer_question, summarize, deepen, build_exercises, build_reasoning
from studyforge.assessment import grade_answer
from studyforge.coverage import analyze_coverage
from studyforge.student import weakest, mastery_for
from studyforge.curriculum import create_curriculum, list_curricula, curriculum_nodes, curriculum_document_ids, next_node, set_node_status, delete_curriculum
from studyforge.workspaces import ensure_default_workspace, create_workspace, list_workspaces, get_workspace
from studyforge.notes import create_note, list_notes, delete_note
from studyforge.sessions import start_session, active_sessions
from studyforge.knowledge import rebuild_graph, graph
from studyforge.repetition import due_reviews, upcoming_reviews
from studyforge.interactive import start_exercise_session, session_state as exercise_state, submit_answer

st.set_page_config(page_title='Tutor LLM', page_icon='📚', layout='wide')
ensure_default_workspace()
st.title('Tutor LLM')
st.caption('Workspace isolati · tutor adattivo · knowledge graph · ripasso intelligente · API pronta per iPadOS')

workspaces=list_workspaces(); workspace_labels={f"{w['name']} (#{w['id']})":int(w['id']) for w in workspaces}
with st.sidebar:
    current_label=st.selectbox('Workspace',list(workspace_labels)); workspace_id=workspace_labels[current_label]; workspace=get_workspace(workspace_id)
    if workspace and workspace['goal']: st.caption('Obiettivo: '+workspace['goal'])
    with st.expander('Nuovo workspace'):
        wn=st.text_input('Nome',key='new_workspace_name'); wg=st.text_area('Obiettivo',key='new_workspace_goal'); wd=st.text_area('Descrizione',key='new_workspace_description')
        if st.button('Crea workspace',disabled=not wn):
            try: create_workspace(wn,wd,wg); st.rerun()
            except Exception as e: st.error(str(e))
    epistemic_mode=st.radio('Politica epistemica',['Grounded','Tutor','Expert'],index=1)
    st.write(f"LLM: `{settings.chat_model}`"); st.write(f"Embedding: `{settings.embedding_model}`")
    st.success('Ollama connesso') if health() else st.error('Avvia Ollama su '+settings.ollama_url)
    docs=list_documents(workspace_id); options={f"{r['name']} (#{r['id']})":int(r['id']) for r in docs}
    selected_labels=st.multiselect('Fonti attive',list(options),default=list(options)); selected_ids=[options[x] for x in selected_labels]

(t_library,t_path,t_tutor,t_summary,t_exercises,t_knowledge,t_notes,t_progress)=st.tabs([
    'Biblioteca','Percorso','Tutor','Riassumi / Approfondisci','Esercizi','Mappa / Ripasso','Note','Progressi'])

with t_library:
    files=st.file_uploader('PDF, DOCX, TXT/MD o immagini',accept_multiple_files=True,type=['pdf','docx','txt','md','png','jpg','jpeg','tif','tiff','webp'])
    if st.button('Indicizza nel workspace',disabled=not files):
        for f in files or []:
            with tempfile.NamedTemporaryFile(delete=False,suffix=os.path.splitext(f.name)[1]) as tmp: tmp.write(f.getbuffer()); p=tmp.name
            try:
                with st.spinner('Elaboro '+f.name): r=ingest_file(workspace_id,p,f.name)
                st.success(f"{r['name']}: {r['chunks']} sezioni · layout {r['layout_pages']} pagine · OCR {r['ocr_pages']} pagine")
            except Exception as e: st.error(f'{f.name}: {e}')
            finally:
                try: os.unlink(p)
                except OSError: pass
        st.rerun()
    for d in docs:
        c1,c2=st.columns([5,1]); c1.write(f"**{d['name']}** — {d['created_at'][:10]}")
        if c2.button('Elimina',key=f"del_{workspace_id}_{d['id']}"): delete_document(workspace_id,int(d['id'])); st.rerun()
    if docs:
        st.divider(); st.markdown('**Anteprima contesto pagina (fondazione iPad)**')
        dl=st.selectbox('Documento',list(options),key='page_doc'); pg=st.number_input('Pagina',min_value=1,value=1,key='page_no')
        if st.button('Apri contesto pagina'):
            data=get_document_page(workspace_id,options[dl],int(pg))
            if data:
                st.write(data['text'][:5000]); st.caption(f"blocchi layout: {len(data['blocks'])} · OCR: {'sì' if data['ocr_used'] else 'no'}")
            else: st.warning('Pagina non disponibile nel nuovo formato indicizzato.')

with t_path:
    goal=st.text_input('Obiettivo del percorso',value=(workspace['goal'] if workspace else ''))
    cname=st.text_input('Nome percorso',value='Percorso principale')
    c1,c2=st.columns(2)
    if c1.button('Valuta copertura biblioteca',disabled=not goal or not selected_ids):
        try: st.session_state.coverage=analyze_coverage(workspace_id,goal,selected_ids)
        except Exception as e: st.error(str(e))
    if c2.button('Crea syllabus',disabled=not goal or not selected_ids):
        try: create_curriculum(workspace_id,cname,goal,selected_ids); st.rerun()
        except Exception as e: st.error(str(e))
    if st.session_state.get('coverage'):
        cov=st.session_state.coverage; st.metric('Copertura stimata',f"{float(cov['coverage']):.0%}",cov.get('level_supported','')); st.write(cov.get('library_assessment',''))
        for label,key in [('Solido','strong'),('Parziale','partial'),('Mancante','missing')]:
            if cov.get(key): st.write(f"**{label}:** "+', '.join(str(x.get('topic','')) for x in cov[key]))
    curricula=list_curricula(workspace_id)
    if curricula:
        labels={f"{r['title']} — {r['goal']} (#{r['id']})":int(r['id']) for r in curricula}; cid=labels[st.selectbox('Percorso',list(labels))]
        nxt=next_node(workspace_id,cid)
        if nxt:
            st.info(f"Prossima attività: **{nxt['title']}** — {nxt['description']}")
            if st.button('Genera prossima lezione',type='primary'):
                ids=curriculum_document_ids(workspace_id,cid); lesson,sources=build_lesson(workspace_id,nxt['title'],'Approfondita',ids,epistemic_mode)
                lid=save_lesson(workspace_id,nxt['title'],'Approfondita',lesson,sources,epistemic_mode); set_node_status(int(nxt['id']),'learning')
                st.session_state.update(tutor_content=lesson,tutor_sources=sources,lesson_id=lid,lesson_topic=nxt['title'])
        for r in curriculum_nodes(cid): st.write(f"{r['position']}. **{r['title']}** · {r['status']} · mastery {mastery_for(workspace_id,r['title']):.0%}")
        if st.button('Elimina percorso'): delete_curriculum(workspace_id,cid); st.rerun()

with t_tutor:
    q=st.text_area('Domanda o argomento'); action=st.radio('Azione',['Domanda','Lezione'],horizontal=True); lesson_mode=st.selectbox('Profondità',['Breve','Approfondita','Ripasso'])
    if st.button('Avvia tutor',type='primary',disabled=not q or not selected_ids):
        try:
            if action=='Domanda': content,sources=answer_question(workspace_id,q,selected_ids,epistemic_mode)
            else:
                content,sources=build_lesson(workspace_id,q,lesson_mode,selected_ids,epistemic_mode); save_lesson(workspace_id,q,lesson_mode,content,sources,epistemic_mode)
            st.session_state.update(tutor_content=content,tutor_sources=sources)
        except Exception as e: st.error(str(e))
    if st.session_state.get('tutor_content'):
        st.markdown(st.session_state.tutor_content)
        with st.expander('Evidenze'): st.json(st.session_state.tutor_sources)

with t_summary:
    req=st.text_area('Tema / richiesta',key='summary_request'); action=st.radio('Operazione',['Riassumi','Approfondisci'],horizontal=True)
    if st.button('Genera',key='summary_generate',disabled=not req or not selected_ids):
        try:
            fn=summarize if action=='Riassumi' else deepen; content,sources=fn(workspace_id,req,selected_ids,epistemic_mode); st.session_state.update(study_content=content,study_sources=sources)
        except Exception as e: st.error(str(e))
    if st.session_state.get('study_content'): st.markdown(st.session_state.study_content)

with t_exercises:
    topic=st.text_input('Argomento',key='exercise_topic')
    st.markdown('**Sessione interattiva** — una domanda alla volta, correzione automatica e mastery aggiornata.')
    n=st.slider('Numero esercizi',3,10,6)
    if st.button('Avvia sessione interattiva',disabled=not topic or not selected_ids):
        try:
            sid=start_exercise_session(workspace_id,topic,selected_ids,n,epistemic_mode); st.session_state.exercise_session_id=sid
        except Exception as e: st.error(str(e))
    sid=st.session_state.get('exercise_session_id')
    if sid:
        try:
            state=exercise_state(sid); q=state.get('current_question')
            if q:
                st.info(f"Difficoltà {q.get('difficulty','—')}/5 · {q.get('concept',topic)}\n\n{q['question']}")
                ans=st.text_area('La tua risposta',key=f'ex_answer_{sid}_{state["current_index"]}')
                with st.expander('Indizio'): st.write(q.get('hint',''))
                if st.button('Invia risposta',disabled=not ans,key=f'ex_submit_{sid}_{state["current_index"]}'):
                    st.session_state.exercise_result=submit_answer(sid,ans); st.rerun()
            else: st.success('Sessione completata.')
            if st.session_state.get('exercise_result'):
                r=st.session_state.exercise_result; st.metric('Ultimo punteggio',f"{r['score']:.0%}",f"mastery {r['mastery']:.0%}"); st.write(r['verdict'].get('feedback',''))
        except Exception as e: st.error(str(e))
    st.divider(); st.markdown('**Generazione libera**')
    activity=st.radio('Attività',['Esercizi','Quiz','Ragionamento'],horizontal=True)
    if st.button('Crea attività libera',disabled=not topic or not selected_ids):
        try:
            if activity=='Esercizi': content,_=build_exercises(workspace_id,topic,selected_ids,n=n,epistemic_mode=epistemic_mode)
            elif activity=='Quiz': content=build_quiz(workspace_id,topic,selected_ids,n,epistemic_mode)
            else: content,_=build_reasoning(workspace_id,topic,selected_ids,epistemic_mode)
            st.session_state.activity_content=content
        except Exception as e: st.error(str(e))
    if st.session_state.get('activity_content'): st.markdown(st.session_state.activity_content)

with t_knowledge:
    st.subheader('Knowledge graph del workspace')
    if st.button('Ricostruisci mappa concettuale',disabled=not selected_ids):
        try:
            with st.spinner('Analizzo concetti e relazioni...'): st.session_state.graph_stats=rebuild_graph(workspace_id,selected_ids)
        except Exception as e: st.error(str(e))
    g=graph(workspace_id)
    if g['nodes']:
        st.caption(f"{len(g['nodes'])} concetti · {len(g['edges'])} relazioni")
        for node in g['nodes'][:30]: st.write(f"**{node['name']}** · {node['node_type']} · importanza {float(node['importance']):.0%} — {node['description']}")
        with st.expander('Relazioni'): 
            for e in g['edges'][:80]: st.write(f"{e['source']} → {e['relation']} → {e['target']} ({float(e['strength']):.0%})")
    else: st.info('Costruisci la prima mappa dai documenti del workspace.')
    st.divider(); st.subheader('Ripasso programmato')
    due=due_reviews(workspace_id,30); upcoming=upcoming_reviews(workspace_id,30)
    if due:
        st.warning(f'{len(due)} concetti da ripassare ora')
        for r in due: st.write(f"• **{r['concept']}** · ultimo score {r['last_score'] if r['last_score'] is not None else '—'}")
    else: st.success('Nessun ripasso scaduto.')
    with st.expander('Prossimi ripassi'):
        for r in upcoming: st.write(f"{r['concept']} · {r['due_at'][:10]} · intervallo {r['interval_days']} giorni")

with t_notes:
    title=st.text_input('Titolo nota'); body=st.text_area('Contenuto',height=180)
    doc_for_note=st.selectbox('Collega a documento',['—']+list(options)) if options else '—'; page=st.number_input('Pagina',min_value=0,value=0)
    if st.button('Salva nota',disabled=not title):
        did=options.get(doc_for_note) if doc_for_note!='—' else None; create_note(workspace_id,title,body,document_id=did,page=(int(page) or None)); st.rerun()
    for note in list_notes(workspace_id):
        with st.expander(f"{note['title']} · {note['document_name'] or 'nota libera'}"+(f" · p.{note['page']}" if note['page'] else '')):
            st.write(note['content'] or '—')
            if st.button('Elimina nota',key=f"note_del_{note['id']}"): delete_note(workspace_id,int(note['id'])); st.rerun()

with t_progress:
    rows=weakest(workspace_id,12)
    for r in rows: st.progress(float(r['mastery']),text=f"{r['name']} — {float(r['mastery']):.0%} ({r['attempts']} evidenze)")
    st.subheader('Lezioni recenti')
    for r in recent_lessons(workspace_id,10): st.write(f"#{r['id']} · **{r['topic']}** · {r['mode']} · {r['epistemic_mode']} · voto {r['rating'] or '—'}")
    st.subheader('Study Session')
    if st.button('Avvia nuova Study Session'): start_session(workspace_id,workspace['goal'] if workspace else ''); st.rerun()
    for s in active_sessions(workspace_id): st.write(f"Sessione #{s['id']} · documento {s['current_document_id'] or '—'} · pagina {s['current_page'] or '—'} · concetto {s['current_concept'] or '—'}")
