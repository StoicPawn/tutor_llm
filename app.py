from __future__ import annotations
import os,tempfile
import streamlit as st
from studyforge.config import settings
from studyforge.db import list_documents,save_lesson,rate_lesson,delete_document,recent_lessons
from studyforge.ollama_client import health
from studyforge.pipeline import ingest_file
from studyforge.teacher import build_lesson,build_quiz,answer_question
from studyforge.student import record_result,weakest
from studyforge.curriculum import create_curriculum,list_curricula,curriculum_nodes,curriculum_document_ids,next_node,set_node_status,delete_curriculum

st.set_page_config(page_title='StudyForge Local',page_icon='📚',layout='wide')
st.title('StudyForge Local')
st.caption('Biblioteca locale → tutor adattivo, lezioni verificabili, quiz e memoria di apprendimento.')
with st.sidebar:
 st.subheader('Sistema'); st.write(f"LLM: `{settings.chat_model}`"); st.write(f"Embedding: `{settings.embedding_model}`")
 st.success('Ollama connesso') if health() else st.error('Avvia Ollama su '+settings.ollama_url)
 st.divider(); docs=list_documents(); options={f"{r['name']} (#{r['id']})":r['id'] for r in docs}
 selected_labels=st.multiselect('Fonti attive',list(options),default=list(options)); selected_ids=[options[x] for x in selected_labels]

t1,t2,t3,t4,t5,t6=st.tabs(['Libreria','Percorso','Lezione','Domande','Quiz','Progressi'])
with t1:
 files=st.file_uploader('PDF, DOCX, TXT/MD o immagini',accept_multiple_files=True,type=['pdf','docx','txt','md','png','jpg','jpeg','tif','tiff','webp'])
 if st.button('Indicizza',disabled=not files):
  for f in files or []:
   with tempfile.NamedTemporaryFile(delete=False,suffix=os.path.splitext(f.name)[1]) as tmp: tmp.write(f.getbuffer()); p=tmp.name
   try:
    with st.spinner('Elaboro '+f.name): r=ingest_file(p,f.name)
    st.success(f"{r['name']}: {r['chunks']} sezioni")
   except Exception as e: st.error(f'{f.name}: {e}')
   finally:
    try: os.unlink(p)
    except OSError: pass
  st.rerun()
 if docs:
  st.subheader('Documenti indicizzati')
  for d in docs:
   c1,c2=st.columns([5,1]); c1.write(f"**{d['name']}** — {d['created_at'][:10]}")
   if c2.button('Elimina',key=f"del{d['id']}"): delete_document(d['id']); st.rerun()
with t2:
 st.subheader('Percorso di studio adattivo')
 goal=st.text_input('Obiettivo',placeholder='Es. padroneggiare questo manuale per un esame')
 cname=st.text_input('Nome percorso',value='Il mio percorso')
 if st.button('Analizza i documenti e crea syllabus',disabled=not goal or not selected_ids):
  try:
   with st.spinner('Costruisco concetti e prerequisiti...'): cid=create_curriculum(cname,goal,selected_ids)
   st.session_state.curriculum_id=cid; st.rerun()
  except Exception as e: st.error(str(e))
 curricula=list_curricula()
 if curricula:
  labels={f"{r['title']} — {r['goal']} (#{r['id']})":r['id'] for r in curricula}
  current=st.selectbox('Percorso',list(labels)); cid=labels[current]; st.session_state.curriculum_id=cid
  nxt=next_node(cid)
  if nxt:
   st.info(f"Prossima lezione consigliata: **{nxt['title']}** — {nxt['description']}")
   if st.button('Studia la prossima lezione',type='primary'):
    ids=curriculum_document_ids(cid); lesson,sources=build_lesson(nxt['title'],'Approfondita',ids); lid=save_lesson(nxt['title'],'Approfondita',lesson,sources); set_node_status(nxt['id'],'learning'); st.session_state.update(lesson=lesson,lesson_id=lid,sources=sources,lesson_topic=nxt['title']); st.success('Lezione pronta nella scheda Lezione.')
  for r in curriculum_nodes(cid):
   prereq=', '.join(__import__('json').loads(r['prerequisites_json'])) or '—'; m=__import__('studyforge.student',fromlist=['mastery_for']).mastery_for(r['title'])
   st.write(f"{r['position']}. **{r['title']}** · {r['status']} · padronanza {m:.0%} · prerequisiti: {prereq}")
  if st.button('Elimina percorso'): delete_curriculum(cid); st.rerun()
 else: st.info('Crea il primo percorso dai documenti selezionati.')
with t3:
 topic=st.text_input('Cosa vuoi capire?',placeholder='Es. fenomeno e noumeno in Kant')
 mode=st.radio('Profondità',['Breve','Approfondita','Ripasso'],horizontal=True)
 if st.button('Crea lezione',type='primary',disabled=not topic or not selected_ids):
  with st.spinner('Costruisco la lezione...'):
   try:
    lesson,sources=build_lesson(topic,mode,selected_ids); lid=save_lesson(topic,mode,lesson,sources)
    st.session_state.update(lesson=lesson,lesson_id=lid,sources=sources,lesson_topic=topic)
   except Exception as e: st.error(str(e))
 if st.session_state.get('lesson'):
  st.markdown(st.session_state.lesson)
  with st.expander('Evidenze recuperate'): st.json(st.session_state.sources)
  rating=st.slider('Utilità',1,5,4); feedback=st.text_area('Come migliorare?')
  if st.button('Salva feedback'):
   rate_lesson(st.session_state.lesson_id,rating,feedback); record_result(st.session_state.lesson_topic,(rating-1)/4,'lesson_feedback'); st.success('Profilo aggiornato.')
with t4:
 q=st.text_input('Fai una domanda ai tuoi documenti')
 if st.button('Rispondi dalle fonti',disabled=not q or not selected_ids):
  try:
   ans,src=answer_question(q,selected_ids); st.markdown(ans)
   with st.expander('Evidenze'): st.json(src)
  except Exception as e: st.error(str(e))
with t5:
 qt=st.text_input('Argomento del quiz'); n=st.slider('Domande',4,15,8)
 if st.button('Genera quiz',disabled=not qt or not selected_ids):
  try: st.session_state.quiz=build_quiz(qt,selected_ids,n); st.session_state.quiz_topic=qt
  except Exception as e: st.error(str(e))
 if st.session_state.get('quiz'):
  st.markdown(st.session_state.quiz); score=st.slider('Quanto hai risposto correttamente?',0,100,70)
  if st.button('Registra risultato quiz'): record_result(st.session_state.quiz_topic,score/100,'quiz'); st.success('Padronanza aggiornata.')
with t6:
 st.subheader('Concetti da rinforzare'); rows=weakest(12)
 if rows:
  for r in rows: st.progress(float(r['mastery']),text=f"{r['name']} — {float(r['mastery']):.0%} ({r['attempts']} evidenze)")
 else: st.info('Studia e valuta una lezione o un quiz per costruire il profilo.')
 st.subheader('Lezioni recenti')
 for r in recent_lessons(10): st.write(f"#{r['id']} · **{r['topic']}** · {r['mode']} · voto {r['rating'] or '—'}")
