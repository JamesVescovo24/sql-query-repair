import hashlib
import pytest
from contract import CaseInput,RunInput,RunOutput
from plugin.datasets import CASES
from plugin.logic import pin_reference,read_dataset,save_candidate
from plugin.storage import REPORT_PATH
from verifier import verify_input,verify_output,verify_task

@pytest.mark.parametrize('case', ['region-revenue','overdue-count'])
@pytest.mark.parametrize('seed',[1,77,9999])
def test_fixed_query_passes_all_fixtures(tmp_path,case,seed):
    task=CaseInput(case,seed);pin=pin_reference(task,tmp_path)
    assert verify_output('pin_sql_truth',task,pin,str(tmp_path))['valid']
    read=read_dataset(task,tmp_path)
    assert verify_output('read_sql_case',task,read,str(tmp_path))['valid']
    candidate=RunInput(case,seed,CASES[case]['solution']);output=save_candidate(candidate,tmp_path)
    assert verify_output('run_candidate_sql',candidate,output,str(tmp_path))['valid']
    assert verify_task('repair-sql',task,output,pin,str(tmp_path))['valid']

@pytest.mark.parametrize('case',['region-revenue','overdue-count'])
def test_broken_query_and_constant_query_fail(tmp_path,case):
    task=CaseInput(case,7);pin=pin_reference(task,tmp_path)
    broken=save_candidate(RunInput(case,7,CASES[case]['broken_query']),tmp_path)
    assert not verify_task('repair-sql',task,broken,pin,str(tmp_path))['valid']
    constant='SELECT \"East\" AS region, 0 AS '+CASES[case]['columns'][1]
    output=save_candidate(RunInput(case,7,constant),tmp_path)
    assert not verify_task('repair-sql',task,output,pin,str(tmp_path))['valid']

@pytest.mark.parametrize('unsafe',['DROP TABLE orders','SELECT * FROM orders; DELETE FROM orders','SELECT * FROM orders --hello','UPDATE orders SET status=\'X\'', ''])
def test_unsafe_sql_is_rejected(tmp_path,unsafe):
    assert not verify_input('run_candidate_sql',RunInput('region-revenue',1,unsafe))['valid']
    with pytest.raises(ValueError):
        save_candidate(RunInput('region-revenue',1,unsafe),tmp_path)

def test_unknown_case_and_seed_are_rejected():
    assert not verify_input('read_sql_case',CaseInput('not-a-case',1))['valid']
    assert not verify_input('read_sql_case',CaseInput('region-revenue',0))['valid']

def test_receipt_tampered_malformed_or_missing(tmp_path):
    task=CaseInput('region-revenue',4);pin=pin_reference(task,tmp_path)
    out=save_candidate(RunInput('region-revenue',4,CASES['region-revenue']['solution']),tmp_path)
    (tmp_path/REPORT_PATH).write_bytes(b'{bad')
    assert not verify_task('repair-sql',task,out,pin,str(tmp_path))['valid']
    out.digest=hashlib.sha256(b'{bad').hexdigest()
    assert not verify_task('repair-sql',task,out,pin,str(tmp_path))['valid']
    (tmp_path/REPORT_PATH).unlink()
    assert not verify_task('repair-sql',task,out,pin,str(tmp_path))['valid']

def test_pinned_answer_tamper_detected(tmp_path):
    task=CaseInput('overdue-count',8);pin=pin_reference(task,tmp_path)
    out=save_candidate(RunInput('overdue-count',8,CASES['overdue-count']['solution']),tmp_path)
    pin.expected[0].rows=['[\"East\",9999]']
    assert not verify_task('repair-sql',task,out,pin,str(tmp_path))['valid']
