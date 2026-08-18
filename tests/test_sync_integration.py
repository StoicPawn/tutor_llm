import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

import studyforge.db as db
from studyforge.workspaces import ensure_default_workspace, create_workspace
from studyforge.notes import create_note, update_note, delete_note
from studyforge.annotations import create_annotation
from studyforge.notebooks import create_notebook, get_notebook, save_page
from studyforge.offline_sync import pull_changes, push_change


class SyncIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.old=db.settings
        db.settings=SimpleNamespace(db_path=str(root/'studyforge.db'),upload_dir=str(root/'uploads'))
        ensure_default_workspace(); self.wid=create_workspace('Sync Math')
        self.doc_id=db.add_document(self.wid,'book.pdf',str(root/'book.pdf'))

    def tearDown(self):
        db.settings=self.old; self.tmp.cleanup()

    def test_normal_note_crud_emits_sync_revisions_and_tombstone(self):
        nid=create_note(self.wid,'N','v1')
        first=pull_changes(self.wid,0)
        note=[c for c in first['changes'] if c['object']['entity_type']=='note'][-1]['object']
        self.assertEqual(note['server_id'],nid); self.assertEqual(note['revision'],1)
        update_note(self.wid,nid,content='v2')
        second=pull_changes(self.wid,first['cursor'])
        self.assertEqual(second['changes'][-1]['object']['revision'],2)
        self.assertEqual(second['changes'][-1]['object']['payload']['content'],'v2')
        delete_note(self.wid,nid)
        third=pull_changes(self.wid,second['cursor'])
        self.assertTrue(third['changes'][-1]['object']['deleted'])
        self.assertEqual(third['changes'][-1]['operation'],'delete')

    def test_offline_note_push_materializes_and_conflict_is_non_destructive(self):
        cid=str(uuid.uuid4())
        created=push_change(self.wid,'note',cid,0,{'title':'Offline','content':'one','kind':'text'})
        sid=created['object']['server_id']
        with db.connect() as con:
            self.assertEqual(con.execute('SELECT content FROM notes WHERE id=?',(sid,)).fetchone()['content'],'one')
        updated=push_change(self.wid,'note',cid,1,{'title':'Offline','content':'two','kind':'text'})
        self.assertEqual(updated['object']['revision'],2)
        conflict=push_change(self.wid,'note',cid,1,{'title':'Offline','content':'stale','kind':'text'})
        self.assertEqual(conflict['status'],'conflict')
        with db.connect() as con:
            self.assertEqual(con.execute('SELECT content FROM notes WHERE id=?',(sid,)).fetchone()['content'],'two')
        deleted=push_change(self.wid,'note',cid,2,{},deleted=True)
        self.assertTrue(deleted['object']['deleted'])
        with db.connect() as con:
            self.assertIsNone(con.execute('SELECT 1 FROM notes WHERE id=?',(sid,)).fetchone())

    def test_annotations_and_notebook_pages_emit_and_materialize(self):
        aid=create_annotation(self.wid,self.doc_id,1,'highlight',bbox=[1,2,3,4],text='x')
        changes=pull_changes(self.wid,0)['changes']
        ann=[c['object'] for c in changes if c['object']['entity_type']=='annotation'][-1]
        self.assertEqual(ann['server_id'],aid)

        notebook_id=create_notebook(self.wid,'Q')
        page=get_notebook(self.wid,notebook_id)['pages'][0]
        save_page(self.wid,notebook_id,page['id'],layers=[{'kind':'text','text':'hello'}])
        all_changes=pull_changes(self.wid,0)['changes']
        pages=[c['object'] for c in all_changes if c['object']['entity_type']=='notebook_page']
        self.assertGreaterEqual(pages[-1]['revision'],2)

        cid=str(uuid.uuid4())
        pushed=push_change(self.wid,'notebook_page',cid,0,{
            'notebook_id':notebook_id,'position':2,'title':'Offline page','background':'grid',
            'width':1024,'height':1365,'layers':[{'kind':'text','text':'from ipad'}]
        })
        new_id=pushed['object']['server_id']
        nb=get_notebook(self.wid,notebook_id)
        materialized=[p for p in nb['pages'] if p['id']==new_id][0]
        self.assertEqual(materialized['background'],'grid')
        self.assertEqual(materialized['layers'][0]['text'],'from ipad')

        second=push_change(self.wid,'notebook_page',str(uuid.uuid4()),0,{
            'notebook_id':notebook_id,'position':2,'title':'Collision','background':'blank','layers':[]
        })
        second_page=[p for p in get_notebook(self.wid,notebook_id)['pages'] if p['id']==second['object']['server_id']][0]
        self.assertNotEqual(second_page['position'],2)

    def test_sync_cannot_reference_document_from_another_workspace(self):
        other=create_workspace('Other')
        other_doc=db.add_document(other,'other.pdf','/tmp/other.pdf')
        with self.assertRaises(ValueError):
            push_change(self.wid,'note',str(uuid.uuid4()),0,{'title':'bad','document_id':other_doc})
        with self.assertRaises(ValueError):
            push_change(self.wid,'annotation',str(uuid.uuid4()),0,{
                'document_id':other_doc,'page':1,'kind':'highlight','bbox':[0,0,1,1]
            })


if __name__=='__main__': unittest.main()
