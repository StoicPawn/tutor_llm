from __future__ import annotations
import streamlit as st
from studyforge.workspaces import ensure_default_workspace, list_workspaces, get_workspace
from studyforge.db import list_documents
from studyforge.notebooks import create_notebook, list_notebooks, get_notebook, add_page, save_page, delete_notebook

st.set_page_config(page_title='Tutor LLM · Quaderno', page_icon='📝', layout='wide')
ensure_default_workspace()
st.title('Quaderno')
st.caption('Fogli persistenti collegabili a documenti, pagine e concetti · modello pronto per Apple Pencil')

workspaces=list_workspaces(); labels={f"{w['name']} (#{w['id']})":int(w['id']) for w in workspaces}
with st.sidebar:
    workspace_id=labels[st.selectbox('Workspace',list(labels))]
    workspace=get_workspace(workspace_id)
    if workspace and workspace['goal']: st.caption('Obiettivo: '+workspace['goal'])

docs=list_documents(workspace_id); doc_options={'—':None}|{f"{d['name']} (#{d['id']})":int(d['id']) for d in docs}

with st.expander('Nuovo quaderno',expanded=not bool(list_notebooks(workspace_id))):
    title=st.text_input('Titolo',value='Quaderno di studio')
    description=st.text_area('Descrizione')
    linked_doc_label=st.selectbox('Collega a documento',list(doc_options),key='nb_doc')
    linked_page=st.number_input('Pagina collegata',min_value=0,value=0)
    concept=st.text_input('Concetto collegato')
    if st.button('Crea quaderno',type='primary',disabled=not title.strip()):
        nid=create_notebook(workspace_id,title,description,document_id=doc_options[linked_doc_label],page=int(linked_page) or None,concept=concept or None)
        st.session_state.notebook_id=nid; st.rerun()

books=list_notebooks(workspace_id)
if not books:
    st.info('Crea il primo quaderno nel workspace.')
    st.stop()
book_labels={f"{b['title']} · {b['page_count']} pagine (#{b['id']})":int(b['id']) for b in books}
default_id=st.session_state.get('notebook_id')
default_label=next((k for k,v in book_labels.items() if v==default_id),list(book_labels)[0])
selected=st.selectbox('Quaderno',list(book_labels),index=list(book_labels).index(default_label))
notebook_id=book_labels[selected]; st.session_state.notebook_id=notebook_id
book=get_notebook(workspace_id,notebook_id)

meta1,meta2,meta3=st.columns([4,2,1])
meta1.markdown(f"### {book['title']}")
meta1.caption(book.get('description') or 'Nessuna descrizione')
link=[]
if book.get('linked_document_id'): link.append(f"documento #{book['linked_document_id']}")
if book.get('linked_page'): link.append(f"p.{book['linked_page']}")
if book.get('linked_concept'): link.append(book['linked_concept'])
meta2.write(' · '.join(link) if link else 'Quaderno libero')
if meta3.button('Elimina quaderno'):
    delete_notebook(workspace_id,notebook_id); st.session_state.pop('notebook_id',None); st.rerun()

pages=book['pages']; page_labels={f"{p['position']}. {p['title']} (#{p['id']})":int(p['id']) for p in pages}
left,right=st.columns([1.25,1],gap='large')
with left:
    selected_page_label=st.selectbox('Pagina',list(page_labels)); page_id=page_labels[selected_page_label]
    page=next(p for p in pages if int(p['id'])==page_id)
    st.caption(f"Canvas {page['width']:.0f} × {page['height']:.0f} · sfondo {page['background']}")
    st.markdown('---')
    text_layers=[x for x in page['layers'] if x.get('kind')=='text']
    source_layers=[x for x in page['layers'] if x.get('kind')=='source_ref']
    ink_layers=[x for x in page['layers'] if x.get('kind')=='ink']
    body='\n\n'.join(str(x.get('text','')) for x in text_layers)
    edited=st.text_area('Foglio testuale',value=body,height=500,placeholder='Scrivi appunti. Sul client iPad questa stessa pagina ospiterà handwriting e disegno vettoriale.')
    background=st.selectbox('Sfondo',['blank','ruled','grid','dot'],index=['blank','ruled','grid','dot'].index(page['background']))
    if st.button('Salva pagina',type='primary'):
        preserved=[x for x in page['layers'] if x.get('kind') not in {'text'}]
        if edited.strip(): preserved.append({'kind':'text','text':edited,'x':64,'y':64,'width':896})
        save_page(workspace_id,notebook_id,page_id,layers=preserved,title=page['title'],background=background)
        st.success('Pagina salvata.'); st.rerun()
    if source_layers:
        with st.expander('Riferimenti a fonti'):
            for x in source_layers: st.write(f"• {x.get('label','Fonte')} — doc {x.get('document_id','—')} p.{x.get('page','—')}")
    if ink_layers:
        total=sum(len(s.get('points',[])) for layer in ink_layers for s in layer.get('strokes',[]))
        st.info(f'Questa pagina contiene {len(ink_layers)} layer ink / {total} punti vettoriali, visualizzabili pienamente nel futuro client Pencil.')

with right:
    st.subheader('Pagine e collegamenti')
    new_title=st.text_input('Titolo nuova pagina',value=f"Pagina {len(pages)+1}")
    new_bg=st.selectbox('Sfondo nuova pagina',['blank','ruled','grid','dot'],key='new_page_bg')
    if st.button('Aggiungi pagina'):
        add_page(workspace_id,notebook_id,title=new_title,background=new_bg); st.rerun()
    st.divider()
    st.markdown('**Aggiungi riferimento al materiale**')
    ref_doc_label=st.selectbox('Documento',list(doc_options),key='ref_doc')
    ref_page=st.number_input('Pagina fonte',min_value=0,value=0,key='ref_page')
    ref_label=st.text_input('Etichetta',value='Riferimento')
    ref_excerpt=st.text_area('Estratto / nota sul riferimento',height=100)
    if st.button('Inserisci riferimento',disabled=doc_options[ref_doc_label] is None):
        layers=list(page['layers'])
        layers.append({'kind':'source_ref','document_id':doc_options[ref_doc_label],'page':int(ref_page) or None,'label':ref_label,'excerpt':ref_excerpt})
        save_page(workspace_id,notebook_id,page_id,layers=layers)
        st.success('Riferimento aggiunto.'); st.rerun()
    st.divider()
    st.markdown('**Struttura Pencil prevista**')
    st.code("{'kind':'ink','strokes':[{'tool':'pen','width':2.0,'points':[[x,y,pressure], ...]}]}",language='python')
    st.caption('Il backend salva già stroke vettoriali; il disegno vero verrà catturato dal canvas nativo iPad senza modificare il modello dati.')
