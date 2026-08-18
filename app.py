from __future__ import annotations
import json, os, tempfile
import streamlit as st
from studyforge.config import settings
from studyforge.db import list_documents, save_lesson, delete_document, recent_lessons
from studyforge.ollama_client import health
from studyforge.pipeline import ingest_file
from studyforge.teacher import build_lesson, build_quiz, answer_question, summarize, deepen, build_exercises, build_reasoning
from studyforge.assessment import grade_answer
from studyforge.coverage import analyze_coverage
from studyforge.student import record_result, weakest, mastery_for
from studyforge.curriculum import create_curriculum, list_curricula, curriculum_nodes, curriculum_document_ids, next_node, set_node_status, delete_curriculum
from studyforge.workspaces import ensure_default_workspace, create_workspace, list_workspaces, get_workspace
from studyforge.notes import create_note, list_notes, delete_note
from studyforge.sessions import start_session, active_sessions

st.set_page_config(page_title='Tutor LLM', page_icon='📚', layout='wide')
ensure_default_workspace()
st.title('Tutor LLM')
st.caption('Workspace di studio isolati · biblioteca personale · tutor adattivo · provenance · API pronta per web/iPadOS')

workspaces = list_workspaces()
workspace_labels = {f"{w['name']} (#{w['id']})": int(w['id']) for w in workspaces}
with st.sidebar:
    st.subheader('Workspace')
    current_label = st.selectbox('Mondo di studio', list(workspace_labels))
    workspace_id = workspace_labels[current_label]
    workspace = get_workspace(workspace_id)
    if workspace and workspace['goal']:
        st.caption('Obiettivo: ' + workspace['goal'])
    with st.expander('Nuovo workspace'):
        wn = st.text_input('Nome', key='new_workspace_name')
        wg = st.text_area('Obiettivo', key='new_workspace_goal')
        wd = st.text_area('Descrizione', key='new_workspace_description')
        if st.button('Crea workspace', disabled=not wn):
            try:
                create_workspace(wn, wd, wg); st.rerun()
            except Exception as e: st.error(str(e))
    st.divider()
    epistemic_mode = st.radio('Politica epistemica', ['Grounded','Tutor','Expert'], index=1,
                               help='Grounded: solo fonti. Tutor: fonti primarie + integrazioni marcate. Expert: anche gap della biblioteca.')
    st.subheader('Sistema')
    st.write(f"LLM: `{settings.chat_model}`")
    st.write(f"Embedding: `{settings.embedding_model}`")
    st.success('Ollama connesso') if health() else st.error('Avvia Ollama su ' + settings.ollama_url)
    st.divider()
    docs = list_documents(workspace_id)
    options = {f"{r['name']} (#{r['id']})": int(r['id']) for r in docs}
    selected_labels = st.multiselect('Fonti attive', list(options), default=list(options))
    selected_ids = [options[x] for x in selected_labels]

(t_library, t_path, t_tutor, t_summary, t_exercises, t_notes, t_progress) = st.tabs([
    'Biblioteca', 'Percorso', 'Tutor', 'Riassumi / Approfondisci', 'Esercizi / Ragionamento', 'Note', 'Progressi'
])

with t_library:
    st.subheader(workspace['name'] if workspace else 'Biblioteca')
    files = st.file_uploader('PDF, DOCX, TXT/MD o immagini', accept_multiple_files=True,
                             type=['pdf','docx','txt','md','png','jpg','jpeg','tif','tiff','webp'])
    if st.button('Indicizza nel workspace', disabled=not files):
        for f in files or []:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as tmp:
                tmp.write(f.getbuffer()); p = tmp.name
            try:
                with st.spinner('Elaboro ' + f.name):
                    r = ingest_file(workspace_id, p, f.name)
                st.success(f"{r['name']}: {r['chunks']} sezioni indicizzate")
            except Exception as e:
                st.error(f'{f.name}: {e}')
            finally:
                try: os.unlink(p)
                except OSError: pass
        st.rerun()
    if docs:
        for d in docs:
            c1, c2 = st.columns([5,1])
            c1.write(f"**{d['name']}** — {d['created_at'][:10]}")
            if c2.button('Elimina', key=f"del_{workspace_id}_{d['id']}"):
                delete_document(workspace_id, int(d['id'])); st.rerun()
    else:
        st.info('Questo workspace non contiene ancora documenti.')

with t_path:
    st.subheader('Percorso di studio adattivo')
    goal = st.text_input('Obiettivo del percorso', value=(workspace['goal'] if workspace else ''),
                         placeholder='Es. arrivare a un livello avanzato di analisi matematica')
    cname = st.text_input('Nome percorso', value='Percorso principale')
    c_cov, c_syl = st.columns(2)
    if c_cov.button('Valuta copertura biblioteca', disabled=not goal or not selected_ids):
        try:
            with st.spinner('Valuto cosa copre davvero la biblioteca...'):
                st.session_state.coverage = analyze_coverage(workspace_id, goal, selected_ids)
        except Exception as e: st.error(str(e))
    if c_syl.button('Crea syllabus', disabled=not goal or not selected_ids):
        try:
            with st.spinner('Costruisco concetti e prerequisiti...'):
                create_curriculum(workspace_id, cname, goal, selected_ids)
            st.rerun()
        except Exception as e: st.error(str(e))
    if st.session_state.get('coverage'):
        cov = st.session_state.coverage
        st.metric('Copertura stimata', f"{float(cov['coverage']):.0%}", cov.get('level_supported',''))
        st.write(cov.get('library_assessment',''))
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('**Solido**')
            for x in cov.get('strong',[]): st.write('✓ ' + str(x.get('topic','')))
        with c2:
            st.markdown('**Parziale**')
            for x in cov.get('partial',[]): st.write('△ ' + str(x.get('topic','')))
        with c3:
            st.markdown('**Mancante**')
            for x in cov.get('missing',[]): st.write('○ ' + str(x.get('topic','')))
        if cov.get('recommended_next'):
            st.markdown('**Prossimi passi consigliati**')
            for i, x in enumerate(cov['recommended_next'],1): st.write(f"{i}. {x}")
    curricula = list_curricula(workspace_id)
    if curricula:
        labels = {f"{r['title']} — {r['goal']} (#{r['id']})": int(r['id']) for r in curricula}
        cid = labels[st.selectbox('Percorso', list(labels))]
        nxt = next_node(workspace_id, cid)
        if nxt:
            st.info(f"Prossima attività consigliata: **{nxt['title']}** — {nxt['description']}")
            if st.button('Genera la prossima lezione', type='primary'):
                ids = curriculum_document_ids(workspace_id, cid)
                lesson, sources = build_lesson(workspace_id, nxt['title'], 'Approfondita', ids, epistemic_mode)
                lid = save_lesson(workspace_id, nxt['title'], 'Approfondita', lesson, sources, epistemic_mode)
                set_node_status(int(nxt['id']), 'learning')
                st.session_state.update(lesson=lesson, lesson_id=lid, sources=sources, lesson_topic=nxt['title'])
        for r in curriculum_nodes(cid):
            prereq = ', '.join(json.loads(r['prerequisites_json'])) or '—'
            m = mastery_for(workspace_id, r['title'])
            st.write(f"{r['position']}. **{r['title']}** · {r['status']} · mastery {m:.0%} · prerequisiti: {prereq}")
        if st.button('Elimina percorso'):
            delete_curriculum(workspace_id, cid); st.rerun()
    else:
        st.info('Crea un percorso usando i documenti di questo workspace.')

with t_tutor:
    st.subheader('Tutor')
    q = st.text_area('Domanda o argomento', placeholder='Chiedi una spiegazione, una connessione o un passaggio che non hai capito')
    c1, c2 = st.columns(2)
    action = c1.selectbox('Azione', ['Domanda','Lezione'])
    lesson_mode = c2.selectbox('Profondità', ['Breve','Approfondita','Ripasso'])
    if st.button('Avvia tutor', type='primary', disabled=not q or not selected_ids):
        try:
            if action == 'Domanda':
                content, sources = answer_question(workspace_id, q, selected_ids, epistemic_mode)
            else:
                content, sources = build_lesson(workspace_id, q, lesson_mode, selected_ids, epistemic_mode)
                lid = save_lesson(workspace_id, q, lesson_mode, content, sources, epistemic_mode)
                st.session_state.update(lesson_id=lid, lesson_topic=q)
            st.session_state.update(tutor_content=content, tutor_sources=sources)
        except Exception as e: st.error(str(e))
    if st.session_state.get('tutor_content'):
        st.markdown(st.session_state.tutor_content)
        with st.expander('Evidenze recuperate'): st.json(st.session_state.tutor_sources)

with t_summary:
    st.subheader('Riassumi o approfondisci')
    req = st.text_area('Tema / richiesta', key='summary_request', placeholder='Es. riassumi le diverse definizioni di convergenza e confrontale')
    action = st.radio('Operazione', ['Riassumi','Approfondisci'], horizontal=True)
    if st.button('Genera', key='summary_generate', disabled=not req or not selected_ids):
        try:
            fn = summarize if action == 'Riassumi' else deepen
            content, sources = fn(workspace_id, req, selected_ids, epistemic_mode)
            st.session_state.update(study_content=content, study_sources=sources)
        except Exception as e: st.error(str(e))
    if st.session_state.get('study_content'):
        st.markdown(st.session_state.study_content)
        with st.expander('Evidenze'): st.json(st.session_state.study_sources)

with t_exercises:
    st.subheader('Esercizi, quiz e ragionamento')
    topic = st.text_input('Argomento', key='exercise_topic')
    activity = st.radio('Attività', ['Esercizi','Quiz','Ragionamento'], horizontal=True)
    n = st.slider('Numero', 4, 12, 6)
    if st.button('Crea attività', disabled=not topic or not selected_ids):
        try:
            if activity == 'Esercizi':
                content, sources = build_exercises(workspace_id, topic, selected_ids, n=n, epistemic_mode=epistemic_mode)
            elif activity == 'Quiz':
                content = build_quiz(workspace_id, topic, selected_ids, n, epistemic_mode); sources = []
            else:
                content, sources = build_reasoning(workspace_id, topic, selected_ids, epistemic_mode)
            st.session_state.update(activity_content=content, activity_sources=sources, activity_topic=topic)
        except Exception as e: st.error(str(e))
    if st.session_state.get('activity_content'):
        st.markdown(st.session_state.activity_content)
    st.divider()
    st.markdown('**Correzione automatica di una risposta**')
    grade_question = st.text_area('Domanda da valutare', key='grade_question')
    grade_answer_text = st.text_area('La tua risposta', key='grade_answer')
    if st.button('Correggi e aggiorna mastery', disabled=not topic or not grade_question or not grade_answer_text or not selected_ids):
        try:
            with st.spinner('Valuto la risposta sulle fonti...'):
                st.session_state.grade_result = grade_answer(workspace_id, topic, grade_question, grade_answer_text, selected_ids)
        except Exception as e: st.error(str(e))
    if st.session_state.get('grade_result'):
        g = st.session_state.grade_result
        st.metric('Valutazione', f"{float(g['score']):.0%}", f"mastery {float(g['mastery']):.0%}")
        st.write(g.get('feedback',''))
        if g.get('correct'): st.success('Corretto: ' + '; '.join(g['correct']))
        if g.get('missing'): st.warning('Da completare: ' + '; '.join(g['missing']))
        if g.get('errors'): st.error('Errori: ' + '; '.join(g['errors']))
        if g.get('next_question'): st.info('Prossima domanda: ' + g['next_question'])

with t_notes:
    st.subheader('Note e fogli di studio')
    title = st.text_input('Titolo nota')
    body = st.text_area('Contenuto', height=180, placeholder='Le note sono artefatti personali e restano separate dalle fonti autorevoli.')
    doc_for_note = st.selectbox('Collega a documento (opzionale)', ['—'] + list(options)) if options else '—'
    page = st.number_input('Pagina (opzionale)', min_value=0, value=0)
    if st.button('Salva nota', disabled=not title):
        did = options.get(doc_for_note) if doc_for_note != '—' else None
        create_note(workspace_id, title, body, document_id=did, page=(int(page) or None))
        st.rerun()
    for note in list_notes(workspace_id):
        label = f"{note['title']} · {note['document_name'] or 'nota libera'}" + (f" · p.{note['page']}" if note['page'] else '')
        with st.expander(label):
            st.write(note['content'] or '—')
            if st.button('Elimina nota', key=f"note_del_{note['id']}"):
                delete_note(workspace_id, int(note['id'])); st.rerun()

with t_progress:
    st.subheader('Concetti da rinforzare')
    rows = weakest(workspace_id, 12)
    if rows:
        for r in rows:
            st.progress(float(r['mastery']), text=f"{r['name']} — {float(r['mastery']):.0%} ({r['attempts']} evidenze)")
    else:
        st.info('Le attività valutate costruiranno il profilo di mastery di questo workspace.')
    st.subheader('Lezioni recenti')
    for r in recent_lessons(workspace_id, 10):
        st.write(f"#{r['id']} · **{r['topic']}** · {r['mode']} · {r['epistemic_mode']} · voto {r['rating'] or '—'}")
    st.subheader('Sessioni di studio')
    if st.button('Avvia nuova Study Session'):
        start_session(workspace_id, workspace['goal'] if workspace else ''); st.rerun()
    for s in active_sessions(workspace_id):
        st.write(f"Sessione #{s['id']} · documento {s['current_document_id'] or '—'} · pagina {s['current_page'] or '—'} · concetto {s['current_concept'] or '—'}")
