import argparse
from playwright.sync_api import sync_playwright, expect
parser=argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8021")
args=parser.parse_args()
import argparse
parser=argparse.ArgumentParser()
parser.add_argument("--url",default="http://127.0.0.1:8018")
args=parser.parse_args()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page()
 requests=[]
 page.on('request',lambda r: requests.append(r.url) if r.url.endswith('/api/plan') else None)
 page.goto(args.url)
 page.get_by_role('button',name='Skip intro').click()
 page.get_by_role('button',name='CSP vs A*',exact=True).click()
 expect(page.get_by_role('button',name='Compare CSP and A*',exact=True)).to_be_disabled()
 page.get_by_role('button',name='Semester plan',exact=True).click()
 page.get_by_role('button',name='Generate plan (A*)',exact=True).click()
 page.get_by_text('Schedule independently verified',exact=True).wait_for(timeout=35000)
 assert len(requests)==1
 page.get_by_role('button',name='CSP vs A*',exact=True).click()
 page.get_by_role('button',name='Compare CSP and A*',exact=True).click()
 page.get_by_text('Comparison finished. Changing plan inputs clears these results.',exact=True).wait_for(timeout=45000)
 assert len(requests)==3
 page.get_by_role('button',name='Semester plan',exact=True).click()
 page.reload()
 page.get_by_text('Schedule independently verified',exact=True).wait_for()
 assert len(requests)==3
 page.get_by_role('button',name='CSP vs A*',exact=True).click()
 page.get_by_text('Comparison finished. Changing plan inputs clears these results.',exact=True).wait_for()
 page.get_by_role('button',name='Saved plans (1)',exact=True).click()
 page.get_by_role('button',name='Open active plan',exact=True).click()
 page.get_by_text('Schedule independently verified',exact=True).wait_for()
 assert len(requests)==3
 page.get_by_role('combobox',name='Target semester').select_option('7')
 page.get_by_role('button',name='Saved plans (1)',exact=True).click()
 page.get_by_role('button',name='Open active plan',exact=True).click()
 page.get_by_text('Schedule independently verified',exact=True).wait_for()
 assert len(requests)==3
 page.get_by_role('button',name='CSP vs A*',exact=True).click()
 page.get_by_text('Comparison finished. Changing plan inputs clears these results.',exact=True).wait_for()
 print('PASS: None generation, comparison gated/real/persisted, saved schedule opens without solver, generated snapshot survives draft edits')
 b.close()
