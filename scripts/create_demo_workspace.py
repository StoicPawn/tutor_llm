from __future__ import annotations
import os, tempfile
from studyforge.workspaces import create_workspace, list_workspaces
from studyforge.pipeline import ingest_file

DOCS={
'01_limiti.md': '''# Fondamenti di Analisi\n\n## 1. Limiti\nIl limite descrive il comportamento di una funzione vicino a un punto. Dire che lim x→a f(x)=L significa che i valori di f(x) possono essere resi arbitrariamente vicini a L prendendo x sufficientemente vicino ad a.\n\n### 1.1 Continuità\nUna funzione è continua in a se il limite per x→a coincide con f(a).\n\n## 2. Derivate\nLa derivata è il limite del rapporto incrementale e misura la variazione locale della funzione.\n''',
'02_integrali.md': '''# Integrazione\n\n## 1. Integrale di Riemann\nL'integrale di Riemann approssima l'area tramite somme su partizioni dell'intervallo.\n\n## 2. Teorema fondamentale del calcolo\nSotto opportune ipotesi, derivazione e integrazione sono operazioni inverse. Se F(x)=∫_a^x f(t)dt e f è continua, allora F'(x)=f(x).\n\n### 2.1 Collegamento con le derivate\nIl teorema unisce il problema locale della derivata con quello globale dell'area.\n'''
}


def main():
    existing={r['name']:int(r['id']) for r in list_workspaces()}
    if 'Matematica Demo' in existing:
        raise SystemExit('Il workspace Matematica Demo esiste già: eliminalo prima di rigenerarlo.')
    wid=create_workspace('Matematica Demo','Fixture end-to-end di Tutor LLM.','Comprendere limiti, derivate, integrali e le loro relazioni.')
    with tempfile.TemporaryDirectory() as tmp:
        for name,content in DOCS.items():
            path=os.path.join(tmp,name)
            with open(path,'w',encoding='utf-8') as f: f.write(content)
            result=ingest_file(wid,path,name)
            print(result)
    print(f'Workspace Matematica Demo creato: #{wid}')

if __name__=='__main__': main()
