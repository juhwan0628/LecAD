const video = document.querySelector('#video');
const status = document.querySelector('#status');
const eventText = document.querySelector('#eventText');
const slideToggle = document.querySelector('#slideToggle');
const deicticToggle = document.querySelector('#deicticToggle');
let manifest = null;
let fired = new Set();

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'ko-KR';
  speechSynthesis.speak(u);
}

async function init() {
  const params = new URLSearchParams(location.search);
  const manifestUrl = params.get('manifest') || '../output/manifest.json';
  const response = await fetch(manifestUrl);
  manifest = await response.json();
  if (manifest.source) video.src = params.get('video') || manifest.source;
  status.textContent = `접근성 이벤트 ${manifest.events.length}개를 불러왔습니다.`;
}

video.addEventListener('timeupdate', () => {
  if (!manifest) return;
  for (const event of manifest.events) {
    const key = `${event.type}:${event.timestamp_s}`;
    if (fired.has(key) || Math.abs(video.currentTime - event.timestamp_s) > 0.35) continue;
    if (event.type === 'slide_change' && !slideToggle.checked) continue;
    if (event.type === 'deictic' && !deicticToggle.checked) continue;
    fired.add(key);
    const text = event.description || (event.type === 'slide_change' ? event.text : `화면 지시 표현: ${event.utterance}`);
    eventText.textContent = text;
    speak(text);
  }
});

video.addEventListener('seeked', () => fired.clear());

document.addEventListener('keydown', (e) => {
  if (e.key.toLowerCase() === 'd') document.querySelector('#describeBtn').click();
});

document.querySelector('#describeBtn').addEventListener('click', () => {
  eventText.textContent = '현재 슬라이드 상세 설명은 VLM provider 연결 후 활성화됩니다.';
  speak(eventText.textContent);
});

init().catch(err => { status.textContent = `오류: ${err.message}`; });
