const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('Testing fortune.html & walk divination requirements...');

const fortuneHtmlPath = path.join(__dirname, '..', 'fortune.html');
const indexHtmlPath = path.join(__dirname, '..', 'index.html');

assert.ok(fs.existsSync(fortuneHtmlPath), 'fortune.html must exist');
const fortuneHtml = fs.readFileSync(fortuneHtmlPath, 'utf8');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

// 1. LIFF SDK inclusion
assert.ok(fortuneHtml.includes('https://static.line-scdn.net/liff/edge/2/sdk.js'), 'LIFF SDK script must be included');

// 2. Essential HTML IDs and classes
const requiredElements = [
  'zenApp',
  'sceneShake',
  'stageContainer',
  'cylinderCanvas',
  'pbarWrap',
  'pbarFill',
  'shakeBtn',
  'btnCylinderSound',
  'spearReadyModal',
  'readyLotName',
  'sceneToss',
  'poe-status-panel',
  'tossTargetLot',
  'dot1',
  'dot2',
  'dot3',
  'shengTipText',
  'poeLeft',
  'poeRight',
  'resultView',
  'resultImage',
  'resultBadge',
  'resultTip',
  'tossBtn',
  'tossBtnLabel',
  'resetBtn',
  'viewPoemBtn',
  'omikujiOverlay',
  'omikujiTitle',
  'omikujiRank',
  'omikujiPoem',
  'omikujiDesc',
  'sendToLineBtn'
];

requiredElements.forEach(elemId => {
  assert.ok(
    fortuneHtml.includes(`id="${elemId}"`) || fortuneHtml.includes(`class="${elemId}"`),
    `Missing required DOM element or class: ${elemId}`
  );
});

// 3. Extract script block and evaluate core logic
const scriptMatch = fortuneHtml.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(scriptMatch, 'Inline script block must be found');
const scriptContent = scriptMatch[1];

// Evaluate in sandbox
const mockWindow = {
  location: { search: '', href: 'https://jerry910127.github.io/smart-temple-liff/fortune.html' },
  addEventListener: () => {}
};
const mockDocument = {
  getElementById: (id) => ({
    innerText: '',
    innerHTML: '',
    style: {},
    classList: { add: () => {}, remove: () => {} },
    disabled: false
  }),
  addEventListener: () => {}
};

const sandbox = {
  window: mockWindow,
  document: mockDocument,
  console: console,
  URLSearchParams: URLSearchParams,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout,
  setInterval: setInterval,
  clearInterval: clearInterval,
  Image: class { constructor() { this.src = ''; } },
  performance: { now: () => Date.now() },
  requestAnimationFrame: () => {},
  navigator: {},
  liff: {
    init: async () => {},
    isLoggedIn: () => false,
    isInClient: () => false
  }
};

const vm = require('vm');
vm.createContext(sandbox);
vm.runInContext(scriptContent, sandbox);

// 4. Verify 100% Shengbei guarantee
assert.ok(typeof sandbox.evaluateTossOutcome === 'function', 'evaluateTossOutcome must be defined');
for (let i = 0; i < 50; i++) {
  const outcome = sandbox.evaluateTossOutcome();
  assert.strictEqual(outcome.type, 'sheng', `Toss outcome must ALWAYS be sheng (Holy Cup), got ${outcome.type}`);
  assert.strictEqual(outcome.leftForm, 'convex');
  assert.strictEqual(outcome.rightForm, 'flat');
  assert.ok(outcome.title.includes('聖杯'), 'Outcome title must contain 聖杯');
}
console.log('✓ 100% 聖杯 (Holy Cups) verified over 50 iterations');

// 5. Verify LOTS_DATABASE is themed around "出去走走轉轉運"
const LOTS_DATABASE = vm.runInContext('LOTS_DATABASE', sandbox);
assert.ok(Array.isArray(LOTS_DATABASE), 'LOTS_DATABASE must be an array');
assert.strictEqual(LOTS_DATABASE.length, 7, 'LOTS_DATABASE must have 7 lots matching sticks');

const walkingKeywords = ['步', '行', '走', '出', '途', '遊', '登', '遠', '新', '氣', '運'];
LOTS_DATABASE.forEach((lot, i) => {
  assert.ok(lot.name, `Lot ${i+1} must have a name`);
  assert.ok(lot.rank, `Lot ${i+1} must have a rank`);
  assert.ok(lot.poem, `Lot ${i+1} must have a poem`);
  assert.ok(lot.desc, `Lot ${i+1} must have a desc`);
  
  const combined = lot.poem + lot.desc;
  const matchCount = walkingKeywords.filter(k => combined.includes(k)).length;
  assert.ok(matchCount >= 3, `Lot ${lot.name} must reflect outdoor/walking/fortune theme (matched ${matchCount} keywords)`);
  assert.ok(
    combined.includes('出') || combined.includes('走') || combined.includes('步') || combined.includes('行'),
    `Lot ${lot.name} must mention stepping out, walking or moving`
  );
});
console.log('✓ All 7 lots and poems are themed around 出去走走轉轉運');

// 6. Verify send to LINE logic
assert.ok(typeof sandbox.handleSendToLine === 'function', 'handleSendToLine must be defined');
assert.ok(fortuneHtml.includes('/api/push_fortune'), 'Must call backend /api/push_fortune');
assert.ok(fortuneHtml.includes('liff.sendMessages'), 'Must support fallback/in-client liff.sendMessages');
console.log('✓ LINE message push to chat room logic verified');

// 7. Verify index.html does NOT put the walk fortune in the main menu/dock UI
assert.ok(!indexHtml.includes('lb-dock-item" href="fortune.html"'), 'index.html dock must not link to fortune.html');
assert.ok(!indexHtml.includes('lb-dock-item" onclick="openWalkFortune()'), 'index.html dock must not have openWalkFortune');
assert.ok(!indexHtml.includes('lb-home-entry-card" href="fortune.html"'), 'index.html home entries must not show fortune.html');
assert.ok(indexHtml.includes("targetPage === 'walk'"), 'index.html should have hidden query redirect for ?page=walk');
console.log('✓ Main page UI is clean (not placed in main page), only standalone URL provided');

console.log('\nALL FORTUNE WALK TESTS PASSED SUCCESSFULLY! 🎉');
