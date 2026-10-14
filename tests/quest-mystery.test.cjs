// Run: node tests/quest-mystery.test.cjs (no dependencies, no network/storage writes).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m => m[1]).filter(s => s.trim());
scripts.forEach((s, i) => new vm.Script(s, {filename:`inline-${i}.js`}));
const source = scripts.join('\n');
function fn(name) {
  const match = source.match(new RegExp(`^    (?:async )?function ${name}\\([^]*?^    }`, 'm'));
  assert.ok(match, `Function found: ${name}`);
  return match[0];
}
const storage = new Map();
const done = new Set();
const nodes = new Map();
function node(id) {
  if (!nodes.has(id)) {
    const classes = new Set();
    nodes.set(id, {style:{}, innerHTML:'', innerText:'', value:'', scrollIntoView(){}, classList:{add:v=>classes.add(v), remove:v=>classes.delete(v), contains:v=>classes.has(v)}});
  }
  return nodes.get(id);
}
const route = {totalSteps:6, checkpoints:Array.from({length:6}, (_,i)=>({id:`wc_${i+1}`, name:`LOCATION_${i}`, lat:24+i/100, lng:120, completed:false}))};
let navCalls = 0, completions = 0;
const context = vm.createContext({
  ROUTES_DATA:{wanchun:route, other:{checkpoints:[{id:'other_1'}]}}, activeRouteId:'wanchun',
  localStorage:{getItem:k=>storage.get(k)}, isCheckpointCompleted:id=>done.has(id),
  document:{getElementById:node}, window:{open(){navCalls++;}},
  gMapInstance:null, gMapMarkers:[], gMapPolyline:null, gMapUserMarker:null,
  currentActivePuzzleIndex:0, userCurrentCoords:null, hasUserGpsFix:false, WANCHUN_PUZZLES_DATA:[{answers:['繡球','球'],story:'culture'}],
  triggerManualBeacon(){completions++;}, updatePuzzleUnlockMoment(){},
  closeQuestPuzzleModal(){}, renderRouteDetailView(){}, openQuestGameFlow(){},
  navigator:{geolocation:{getCurrentPosition(success){success({coords:{latitude:24,longitude:120}});}}},
  calculateHaversine(){return 0;}, isGoogleMapsLoaded:false, console,
});
const helpers = source.slice(source.indexOf('    function getQuestFrontier()'), source.indexOf('    function updatePuzzleUnlockMoment('));
vm.runInContext(fn('readQuestPrologueState') + helpers + ['openLbModal','closeLbModal','openCheckpointGoogleMaps','renderInteractiveTempleFallback','submitPuzzleAnswer','refreshGpsLocation'].map(fn).join('\n'), context);
const run = expr => vm.runInContext(expr, context);
assert.equal(run('getQuestFrontier()'),0);
assert.equal(run('canAccessQuestCheckpoint(0)'),false);
assert.equal(run('getCurrentQuestMapIndex()'),-1);
storage.set('wanchun_quest_prologue_v1', JSON.stringify({version:1,order:['B','A','C'],solved:true,completed:true}));
assert.equal(run('readQuestPrologueState().solved'),true);
assert.equal(run('getQuestFrontier()'),0,'Prologue never completes a paid checkpoint');
assert.equal(run('canAccessQuestCheckpoint(0)'),false,'Free prologue never grants paid access');
assert.equal(run('getCurrentQuestMapIndex()'),-1,'No map destination after prologue');
assert.ok(run('renderMysteryCheckpoints()').includes('序章・她曾有另一個名字'));
assert.ok(!run('renderMysteryCheckpoints()').includes('LOCATION_0'));
for (const value of ['{broken', 'null', JSON.stringify({version:1,order:['B','B'],solved:true}), JSON.stringify({version:2,order:[]})]) {
  storage.set('wanchun_quest_prologue_v1',value);
  assert.equal(run('readQuestPrologueState().solved'),false);
  assert.equal(run('readQuestPrologueState().order.length'),0);
}
storage.delete('wanchun_quest_prologue_v1');
storage.set('wanchun_quest_trial','true');
assert.equal(run('canAccessQuestCheckpoint(0)'),true);
assert.equal(run('canAccessQuestCheckpoint(1)'),false);
for (const bad of [-1,6,1.5,NaN,'0']) assert.equal(context.canAccessQuestCheckpoint(bad),false);
assert.equal(run("canAccessQuestCheckpoint(0, 'other')"),true);
let rendered = run('renderMysteryCheckpoints()');
assert.ok(rendered.includes('LOCATION_0'));
for (let i=1;i<6;i++) assert.ok(!rendered.includes(`LOCATION_${i}`));
assert.ok(!/聖筊擺飾|金色平安符|金紋/.test(rendered));
run('renderInteractiveTempleFallback()');
assert.ok(node('googleMapTrack').innerHTML.includes('LOCATION_0'));
assert.ok(!node('googleMapTrack').innerHTML.includes('LOCATION_1'));
run("openCheckpointGoogleMaps('wanchun', 2)");
assert.equal(navCalls,0);
run('refreshGpsLocation()');
assert.equal(completions,0,'GPS must not solve a quest');
node('puzzleAnswerInput').value='繡';
run('submitPuzzleAnswer()');
assert.equal(completions,0,'Partial answer must not pass');
node('puzzleAnswerInput').value='繡球';
run('submitPuzzleAnswer()');
assert.equal(completions,1);
done.add('wc_1');
assert.equal(run('getQuestFrontier()'),1);
assert.equal(run('getCurrentQuestMapIndex()'),-1,'Trial ends without revealing next destination');
assert.ok(run('renderMysteryCheckpoints()').includes('免費體驗已完成'));
assert.ok(!run('renderMysteryCheckpoints()').includes('LOCATION_1'));
run("openLbModal('questRedeemModal')");
assert.equal(node('questRedeemModal').classList.contains('visible'),false);
storage.set('wanchun_quest_active','true');
Object.assign(context, {
  hasGoogleMapsAuthFailed:false,
  getFootprintMarkerIcon(){return null;},
  google:{maps:{
    Map:class {panTo(){} setCenter(){} setZoom(){} fitBounds(){}},
    Marker:class {constructor(options){this.title=options.title;} setMap(){} setPosition(){} addListener(){}},
    Polyline:class {setMap(){}}, InfoWindow:class {open(){}},
    LatLngBounds:class {extend(){}}, Animation:{DROP:'DROP'}, SymbolPath:{CIRCLE:'circle'}, event:{trigger(){}},
  }},
});
vm.runInContext(fn('renderGoogleMap'),context);
for(let i=1;i<6;i++) {
  assert.equal(run('getCurrentQuestMapIndex()'),i);
  assert.equal(context.canAccessQuestCheckpoint(i),true);
  assert.equal(context.canAccessQuestCheckpoint(i+1),false);
  rendered=run('renderMysteryCheckpoints()');
  assert.ok(rendered.includes(`LOCATION_${i}`));
  for(let j=i+1;j<6;j++) assert.ok(!rendered.includes(`LOCATION_${j}`));
  run("renderGoogleMap('wanchun')");
  assert.equal(context.gMapMarkers.filter(Boolean).length,1,'Only current marker is rendered');
  assert.equal(context.gMapMarkers[i].title,`LOCATION_${i}`);
  done.add(`wc_${i+1}`);
}
assert.equal(run('getQuestFrontier()'),-1);
assert.ok(run('renderMysteryCheckpoints()').includes('揭開神祕小物'));
assert.equal(node('questRedeemModal').classList.contains('visible'),false,'No automatic ending popup');
run("openLbModal('questRedeemModal')");
assert.equal(node('questRedeemModal').classList.contains('visible'),true);
done.clear(); done.add('wc_6');
assert.equal(run('getQuestFrontier()'),0,'Sparse legacy progress cannot reveal future checkpoints');
assert.equal(run('canAccessQuestCheckpoint(5)'),false);
assert.equal((html.match(/id="detailCheckpointsList"/g)||[]).length,1);
assert.ok(!html.includes('placeholder="請輸入謎題解答（例：繡球）"'));
console.log('PASS: inline JS syntax; first visit; trial/paywall; sequential paid journey; history; navigation/fallback spoiler guards; GPS; answers; explicit ending; legacy progress.');
