from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page();page.goto('http://127.0.0.1:8024');page.get_by_role('button',name='Skip intro').click()
 for sem in [3,4,5,6]:
  page.get_by_role('combobox',name='Last finished semester').select_option(str(sem));expect(page.get_by_role('dialog',name='Completed electives')).to_be_visible();page.get_by_role('button',name='Review later').click()
 page.get_by_role('combobox',name='Last finished semester').select_option('4');d=page.get_by_role('dialog',name='Completed electives');d.get_by_role('checkbox').first.check();code=d.locator('strong').first.inner_text();d.get_by_role('button',name='Save and generate remaining plan').click();page.get_by_text('Schedule independently verified',exact=True).wait_for(timeout=30000);assert page.evaluate('(code)=>JSON.parse(localStorage.graphmind_saved_plans_v2)[0].completedCourses.includes(code)',code);print('PASS prompts3/4/5/6, passed elective saved, remaining plan verified');b.close()
