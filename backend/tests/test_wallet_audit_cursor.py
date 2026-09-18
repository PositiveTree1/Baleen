"""Failure-injection tests for the standalone research cursor walker."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('wallet_research', Path(__file__).resolve().parents[2]/'docs/research/audit_wallet_data.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def page(rows, cursor, has_more):
    return {'data':rows,'pagination':{'next_cursor':cursor,'has_more':has_more}}


def test_cursor_retains_original_filters_and_accepts_terminal_empty(monkeypatch):
    calls=[]
    pages=iter([page([{'timestamp':7}], 'abc', True), page([],None,False)])
    def get(path,params):
        calls.append(dict(params));return next(pages)
    monkeypatch.setattr(audit,'get',get)
    rows,cov=audit.walk('/v2/trades',{'user':'wallet','start':1,'end':10,'taker_only':'false','limit':1})
    assert cov['complete'] and len(rows)==1
    assert calls[1]==dict(calls[0],cursor='abc')


@pytest.mark.parametrize('second',[
    {'audit_error':'timeout'},
    page([{'timestamp':7}],'def',True),
    page([{'timestamp':6}],'abc',True),
    page([],'def',True),
    page([],None,True),
])
def test_bad_cursor_walk_preserves_partial_evidence(monkeypatch,second):
    pages=iter([page([{'timestamp':7}],'abc',True),second])
    monkeypatch.setattr(audit,'get',lambda *args:next(pages))
    rows,cov=audit.walk('/v2/trades',{'user':'wallet'})
    assert not cov['complete']
    assert rows[0]['timestamp']==7


def test_page_budget_is_not_history_exhaustion(monkeypatch):
    monkeypatch.setattr(audit,'get',lambda *args:page([{'timestamp':7}],'abc',True))
    rows,cov=audit.walk('/v2/trades',{},max_pages=1)
    assert len(rows)==1 and not cov['complete']
    assert cov['reason']=='audit page budget reached'
