try:
    from playwright.sync_api import sync_playwright
    print('playwright-python available')
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={'width':1920,'height':1080})
        page.goto('http://127.0.0.1:8000/')
        page.wait_for_load_state('networkidle')
        page.click('#nav-tab-validation')
        page.wait_for_timeout(1200)
        page.screenshot(path='validation_check.png')
        vv   = page.evaluate("document.getElementById('validation-view').getBoundingClientRect().height")
        hdr  = page.evaluate("document.querySelector('.glass-header').getBoundingClientRect().height")
        body_ov = page.evaluate("document.body.style.overflow")
        cont_pb = page.evaluate("document.querySelector('.container').style.paddingBottom")
        js_vis = """
(function(){
  var cards=document.querySelectorAll('#csv-cards-container .csv-import-card');
  var vp=window.innerHeight;
  var n=0;
  for(var i=0;i<cards.length;i++){
    var r=cards[i].getBoundingClientRect();
    if(r.top>=0 && r.bottom<=vp) n++;
  }
  return n+'/'+cards.length+' vp='+vp;
})()
"""
        vis = page.evaluate(js_vis)
        print('header_height:', hdr)
        print('validation_view_height:', vv)
        print('body_overflow:', repr(body_ov))
        print('container_paddingBottom:', repr(cont_pb))
        print('visible/total cards + viewport:', vis)
        b.close()
except ImportError:
    print('playwright not installed')
except Exception as ex:
    print('error:', ex)
