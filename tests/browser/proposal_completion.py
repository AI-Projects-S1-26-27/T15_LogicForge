import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:8000")
args=parser.parse_args()
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page();page.goto(args.url);page.get_by_role('button',name='Skip intro').click();page.get_by_role('combobox',name='Planning mode').select_option('transcript');page.get_by_role('combobox',name='Transcript finished semester').select_option('2');page.get_by_role('button',name='Generate plan (A*)',exact=True).click();page.get_by_text('Schedule independently verified',exact=True).wait_for(timeout=30000);assert page.evaluate('JSON.parse(localStorage.graphmind_saved_plans_v2)[0].completedCourses.length')>0;page.get_by_text('Why this placement?',exact=True).first.click();page.reload();expect(page.get_by_role('combobox',name='Planning mode')).to_have_value('transcript');expect(page.get_by_role('combobox',name='Transcript finished semester')).to_have_value('2');page.get_by_text('Schedule independently verified',exact=True).wait_for();page.goto(args.url+"/evaluation.html");page.get_by_role('heading',name='GraphMind volunteer evaluation').wait_for();assert page.get_by_role('button',name='Download anonymous feedback JSON').count()==1;print('PASS transcript mode, passed-core planning, placement traces, reload, volunteer form');b.close()
