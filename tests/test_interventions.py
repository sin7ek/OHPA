import os
os.environ.setdefault("ADMIN_PASSWORD","test-password-123456789")
import asyncio
import pytest
from fastapi import HTTPException
import app
import core

class Request:
    def __init__(self,body):self.body=body
    async def json(self):return self.body

def call(fn,body):return asyncio.run(fn(Request(body)))

def test_intervention_crud(monkeypatch,tmp_path):
    monkeypatch.setattr(core,"DATA",tmp_path)
    core.init()
    t="2026-11-25T10:00:00+01:00"
    t2="2026-11-25T11:00:00+01:00"
    call(app.note,{"time":t,"note":"old"})
    call(app.note,{"time":t2,"note":"other"})
    with pytest.raises(HTTPException) as ex:call(app.note,{"time":t,"note":"overwrite"})
    assert ex.value.status_code==409
    with pytest.raises(HTTPException) as ex:call(app.edit_change,{"original_time":t,"original_note":"old","time":t2,"note":"new"})
    assert ex.value.status_code==409
    call(app.edit_change,{"original_time":t,"original_note":"old","time":t,"note":"corrected"})
    with pytest.raises(HTTPException):call(app.delete_change,{"original_time":t,"original_note":"old"})
    assert len(app.change_list())==2
    call(app.delete_change,{"original_time":t,"original_note":"corrected"})
    assert [r["note"] for r in app.change_list()]==["other"]
