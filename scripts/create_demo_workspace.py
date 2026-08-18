from __future__ import annotations
import os,tempfile
import fitz
from studyforge.workspaces import create_workspace,list_workspaces
from studyforge.pipeline import ingest_file

DOCS={
'01_limiti.pdf':[
('CAPITOLO 1 Limiti','1.1 Definizione\nIl limite descrive il comportamento di una funzione vicino a un punto. Dire che lim x→a f(x)=L significa che i valori di f(x) possono essere resi arbitrariamente vicini a L prendendo x sufficientemente vicino ad a.'),
('1.2 Continuità','Una funzione è continua in a se il limite per x→a coincide con f(a). La continuità collega il comportamento locale della funzione al suo valore effettivo.'),
('CAPITOLO 2 Derivate','2.1 Rapporto incrementale\nLa derivata è il limite del rapporto incrementale e misura la variazione locale della funzione. La derivabilità implica continuità, ma non vale il contrario.'),
],
'02_integrali.pdf':[
('CAPITOLO 1 Integrale di Riemann','1.1 Somme di Riemann\nL integrale di Riemann approssima l area tramite somme associate a partizioni dell intervallo.'),
('CAPITOLO 2 Teorema fondamentale del calcolo','2.1 Derivazione e integrazione\nSotto opportune ipotesi, derivazione e integrazione sono operazioni inverse. Se F(x) è l integrale da a a x di f(t) e f è continua, allora F primo di x è uguale a f(x).'),
('2.2 Collegamento con le derivate','Il teorema fondamentale unisce il problema locale della derivata con quello globale dell area e permette di calcolare integrali tramite primitive.'),
]
}


def _write_pdf(path:str,pages:list[tuple[str,str]]):
    doc=fitz.open()
    for title,body in pages:
        page=doc.new_page(width=595,height=842)
        page.insert_text((60,80),title,fontsize=16)
        rect=fitz.Rect(60,110,535,760)
        page.insert_textbox(rect,body,fontsize=11,lineheight=1.35)
    doc.save(path); doc.close()


def main():
    existing={r['name']:int(r['id']) for r in list_workspaces()}
    if 'Matematica Demo' in existing:
        raise SystemExit('Il workspace Matematica Demo esiste già: eliminalo prima di rigenerarlo.')
    wid=create_workspace('Matematica Demo','Fixture end-to-end di Tutor LLM.','Comprendere limiti, derivate, integrali e le loro relazioni.')
    with tempfile.TemporaryDirectory() as tmp:
        for name,pages in DOCS.items():
            path=os.path.join(tmp,name); _write_pdf(path,pages)
            result=ingest_file(wid,path,name); print(result)
    print(f'Workspace Matematica Demo creato: #{wid}')
    print('Ora puoi aprire Tutor LLM, selezionare Matematica Demo e provare struttura PDF, Tutor, knowledge graph e review.')

if __name__=='__main__':main()
