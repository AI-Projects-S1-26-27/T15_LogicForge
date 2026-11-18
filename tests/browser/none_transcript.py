"""None clears old manual transcripts and stays empty across branch changes/reload."""
import argparse
from playwright.sync_api import sync_playwright, expect
parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8018')
args=parser.parse_args()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page()
    page.goto(args.url)
    page.get_by_role('button',name='Skip intro').click()
    page.get_by_role('combobox',name='Last finished semester').select_option('4')
    page.get_by_role('button',name='Completed courses',exact=False).click()
    page.locator('.transcript-course input').first.uncheck()
    expect(page.get_by_role('checkbox',name='Auto-select this branch',exact=False)).not_to_be_checked()
    page.get_by_role('combobox',name='Discipline branch').select_option('ece')
    page.wait_for_function("JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].branch==='ece'")
    page.get_by_role('combobox',name='Last finished semester').select_option('0')
    for branch in ['cse','eee','ece','e_and_i']:
        page.get_by_role('combobox',name='Discipline branch').select_option(branch)
        page.wait_for_function("JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].completedCourses.length === 0")
        assert page.locator('.transcript-course input:checked').count() == 0
    page.reload()
    page.get_by_role('button',name='Completed courses',exact=False).click()
    expect(page.locator('.transcript-course input').first).to_be_disabled()
    with page.expect_request(lambda r:r.url.endswith('/api/plan') and r.method=='POST') as request:
        page.get_by_role('button',name='Generate plan (A*)',exact=True).click()
    assert request.value.post_data_json['completed_courses'] == []
    assert request.value.post_data_json['current_semester'] == 0
    page.get_by_text('Schedule independently verified',exact=True).wait_for(timeout=45000)
    # A manually edited None transcript saved by older releases is repaired on load.
    page.evaluate("""() => {const key='graphmind_saved_plans_v2';const data=JSON.parse(localStorage.getItem(key)); data[0].completedCourses=['CS F211','CS F212']; data[0].autoCompleteCore=false; localStorage.setItem(key,JSON.stringify(data));}""")
    page.reload()
    page.wait_for_function("JSON.parse(localStorage.getItem('graphmind_saved_plans_v2'))[0].completedCourses.length === 0")
    print('PASS: None resets manual history, branch profiles, reload migration and sends an empty transcript to generation')
    browser.close()
