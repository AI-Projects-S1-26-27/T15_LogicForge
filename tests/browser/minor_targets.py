import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:8000")
args=parser.parse_args()
from playwright.sync_api import sync_playwright
from backend.services.scoped_planner import MINORS
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page();page.goto(args.url);page.get_by_role('button',name='Skip intro').click();page.get_by_role('combobox',name='Target finish').select_option('7')
 for branch in ['cse','eee','ece','e_and_i']:
  page.get_by_role('combobox',name='Discipline branch').select_option(branch)
  for minor,m in MINORS.items():
   if branch in m['excluded_branches']:continue
   page.locator('#minor').select_option(minor)
   page.get_by_role('button',name='Generate plan (A*)',exact=True).click()
   page.get_by_text('Schedule independently verified',exact=True).wait_for(timeout=35000)
   assert page.evaluate('JSON.parse(localStorage.graphmind_saved_plans_v2)[0].audit.minor.coursework_met')
   print(branch,minor,'verified',flush=True)
 print('PASS all19 eligible branch/minor combinations target7 in live browser');b.close()
