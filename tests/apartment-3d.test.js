const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const A = (name, cond) => { if (cond) { console.log('PASS', name); } else { console.log('FAIL', name); process.exitCode = 1; } };
(async () => {
  const b = await chromium.launch({ args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport:{ width:1280, height:860 } });
  const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{if(m.type()==='error')errs.push('C:'+m.text());});
  await p.goto('file:///tmp/apt.html', { waitUntil:'networkidle' });
  await p.waitForTimeout(2500);

  // 1. loads clean
  A('no runtime errors on load', errs.length === 0);
  if (errs.length) console.log('   errors:', errs.join(' | '));
  A('error overlay hidden', await p.evaluate(() => getComputedStyle(document.getElementById('err')).display === 'none'));

  // 2. default layout spawned
  const count0 = await p.evaluate(() => window.__planner.items.length);
  A('default layout has 11 items', count0 === 11);

  // 3. select via API → inspector appears with dims
  await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type === 'Sofa'); window.__planner.select(it); });
  await p.waitForTimeout(150);
  A('inspector visible after select', await p.evaluate(() => document.getElementById('inspector').style.display === 'block'));
  A('inspector shows Sofa', await p.evaluate(() => document.getElementById('ins-name').textContent === 'Sofa'));
  A('width input = 84', await p.evaluate(() => +document.getElementById('ins-w').value === 84));

  // 4. custom measurements: set sofa width to 96
  await p.fill('#ins-w', '96');
  await p.dispatchEvent('#ins-w', 'change');
  await p.waitForTimeout(100);
  const sx = await p.evaluate(() => window.__planner.items.find(i => i.userData.type==='Sofa').scale.x);
  A('custom width scales mesh (96/84)', Math.abs(sx - 96/84) < 1e-6);

  // 5. fixed items can't be resized
  await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type === 'Climate cabinet'); window.__planner.select(it); });
  await p.waitForTimeout(100);
  A('cabinet dims locked', await p.evaluate(() => document.getElementById('ins-w').disabled === true));

  // 6. rotate via R key
  const rot0 = await p.evaluate(() => window.__planner.items.find(i => i.userData.type==='Climate cabinet').rotation.y);
  await p.keyboard.press('r');
  await p.waitForTimeout(100);
  const rot1 = await p.evaluate(() => window.__planner.items.find(i => i.userData.type==='Climate cabinet').rotation.y);
  A('R rotates 90°', Math.abs((rot1-rot0) - Math.PI/2) < 1e-6);
  await p.keyboard.press('r'); await p.keyboard.press('r'); await p.keyboard.press('r');  // back to start

  // 7. drag the sofa with the mouse: project its position to screen, drag 120px right
  const scr = await p.evaluate(() => {
    const it = window.__planner.items.find(i => i.userData.type==='Sofa');
    return { x: it.position.x, z: it.position.z };
  });
  // select sofa & find a screen point over it: use center of canvas trick — instead pick via projecting
  const pt = await p.evaluate(() => {
    const it = window.__planner.items.find(i => i.userData.type==='Sofa');
    const v = it.position.clone(); v.y = 15;
    // project using the planner camera through a render — emulate
    return null;
  });
  // simpler: drive pointer events straight at where raycast hits: search the canvas grid for sofa pixel
  const hitXY = await p.evaluate(() => {
    // brute scan: cast rays over a grid until we hit the sofa
    return new Promise(res => {
      const cnv = document.querySelector('canvas');
      const r = cnv.getBoundingClientRect();
      res({ left: r.left, top: r.top, w: r.width, h: r.height });
    });
  });
  // probe with elementFromPoint not possible; instead simulate drag using evaluate on planner internals:
  const before = scr.x;
  // find screen coords by projecting with the actual camera
  await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type==='Sofa'); window.__planner.select(it); });
  await p.waitForTimeout(250);   // let a frame render so the dim label is positioned
  const sofaScreen = await p.evaluate(() => {
    const it = window.__planner.items.find(i => i.userData.type==='Sofa');
    const lbl = it.userData.dimLabel.element.getBoundingClientRect();
    return { x: lbl.left + lbl.width/2, y: lbl.top + lbl.height/2 + 40 };  // just below the floating label = on the sofa
  });
  await p.mouse.move(sofaScreen.x, sofaScreen.y);
  await p.mouse.down();
  await p.mouse.move(sofaScreen.x + 120, sofaScreen.y, { steps: 8 });
  await p.mouse.up();
  await p.waitForTimeout(120);
  const after = await p.evaluate(() => window.__planner.items.find(i => i.userData.type==='Sofa').position.x);
  A('mouse-drag moves sofa', Math.abs(after - before) > 5);

  // 8. add + duplicate + delete
  await p.selectOption('#add-type', 'Bookshelf');
  await p.click('#add-btn'); await p.waitForTimeout(100);
  A('add increases count', await p.evaluate(() => window.__planner.items.length) === count0 + 1);
  await p.click('#ins-dup'); await p.waitForTimeout(100);
  A('duplicate increases count', await p.evaluate(() => window.__planner.items.length) === count0 + 2);
  await p.click('#ins-del'); await p.waitForTimeout(100);
  await p.evaluate(() => { window.__planner.select(window.__planner.items[window.__planner.items.length-1]); });
  await p.click('#ins-del'); await p.waitForTimeout(100);
  A('delete restores count', await p.evaluate(() => window.__planner.items.length) === count0);

  // 9. persistence: move cabinet, reload, position restored
  await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type==='Climate cabinet'); it.position.x = 400; it.position.z = 200; });
  await p.evaluate(() => localStorage.setItem('llinePlannerLayout-v2', window.__planner.serialize()));
  await p.reload({ waitUntil:'networkidle' }); await p.waitForTimeout(2200);
  const restored = await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type==='Climate cabinet'); return { x: it.position.x, z: it.position.z, n: window.__planner.items.length }; });
  A('layout persists across reload', Math.abs(restored.x-400)<0.2 && Math.abs(restored.z-200)<0.2 && restored.n === count0);

  // 10. reset layout
  await p.click('#layout-reset'); await p.waitForTimeout(150);
  const resetPos = await p.evaluate(() => { const it = window.__planner.items.find(i => i.userData.type==='Climate cabinet'); return it.position.x; });
  A('reset layout restores default cabinet spot', resetPos > 500);

  // 11. toggles
  await p.click('#t-half'); await p.waitForTimeout(80);
  A('low walls scales wallGroup', await p.evaluate(() => Math.abs(window.__planner.wallGroup.scale.y - 0.42) < 1e-6));
  await p.click('#t-walls'); await p.waitForTimeout(80);
  A('walls toggle hides wallGroup', await p.evaluate(() => window.__planner.wallGroup.visible === false));
  await p.click('#t-walls'); await p.click('#t-half'); await p.waitForTimeout(80);
  A('walls restored full height', await p.evaluate(() => window.__planner.wallGroup.visible === true && Math.abs(window.__planner.wallGroup.scale.y - 1) < 1e-6));
  // labels toggle
  await p.click('#t-labels'); await p.waitForTimeout(80);
  const hidden = await p.evaluate(() => window.__planner.roomLabels.every(l => l.visible === false));
  A('labels toggle hides room labels', hidden);
  await p.click('#t-labels');

  // 12. camera presets do not error
  await p.click('#v-top'); await p.waitForTimeout(120);
  await p.click('#v-living'); await p.waitForTimeout(120);
  await p.click('#v-dollhouse'); await p.waitForTimeout(120);
  A('camera presets clean', errs.length === 0);

  // 13. resize window
  await p.setViewportSize({ width: 900, height: 600 }); await p.waitForTimeout(200);
  await p.setViewportSize({ width: 1280, height: 860 }); await p.waitForTimeout(200);
  A('resize clean', errs.length === 0);

  // screenshots for review
  await p.evaluate(() => localStorage.removeItem('llinePlannerLayout-v2'));
  await p.reload({ waitUntil:'networkidle' }); await p.waitForTimeout(2200);
  await p.screenshot({ path:'/tmp/apt_full.png' });
  await p.click('#t-half'); await p.waitForTimeout(400);
  const style = await p.addStyleTag({ content:'#title,#panel,#help,#inspector{display:none !important}' });
  await p.screenshot({ path:'/tmp/apt_lowwalls.png' });
  await p.evaluate(() => window.__planner.setView('living'));
  await p.waitForTimeout(400);
  await p.screenshot({ path:'/tmp/apt_livingcam.png' });

  if (errs.length) console.log('LATE ERRORS:', errs.join(' | '));
  await b.close();
})().catch(e=>{console.error('FATAL', e);process.exit(1);});
