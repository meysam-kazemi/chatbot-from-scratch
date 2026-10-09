const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const assert = require('node:assert/strict');
const html = readFileSync('src/chatbot/static/index.html', 'utf8');
const start = html.indexOf('    async function consumeEvents(');
const end = html.indexOf('    $("message").onkeydown', start);
const consumeEvents = new Function(`${html.slice(start, end)}; return consumeEvents;`)();

function response(text, step = 1) {
  const bytes = new TextEncoder().encode(text);
  return new Response(new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += step) controller.enqueue(bytes.slice(i, i + step));
      controller.close();
    }
  }));
}
function frame(data) { return `event: ${data.event}\ndata: ${JSON.stringify(data)}\n\n`; }

test('handles frames and UTF-8 split across arbitrary byte boundaries', async () => {
  const events = [{ event: 'delta', text: 'سلام 👋\n' }, { event: 'done', title: 'Greeting' }];
  for (const step of [1, 3, 10000]) {
    const received = [];
    await consumeEvents(response(events.map(frame).join(''), step), e => received.push(e));
    assert.deepEqual(received, events);
  }
});
test('reports server errors and preserves partial text', async () => {
  const received = [];
  await assert.rejects(consumeEvents(response(frame({ event: 'delta', text: 'Partial' }) +
    frame({ event: 'error', message: 'Interrupted' })), e => received.push(e)), /Interrupted/);
  assert.equal(received[0].text, 'Partial');
});
test('rejects a stream closed before done', async () => {
  await assert.rejects(consumeEvents(response(frame({ event: 'delta', text: 'Partial' })), () => {}), /Connection closed/);
});
