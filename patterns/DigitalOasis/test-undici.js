// simulate preload
require('./preload.js');
console.log('global.ReadableStream defined?', typeof global.ReadableStream);
console.log('global.ReadableStream.prototype.tee?', typeof global.ReadableStream.prototype.tee);

// try to require undici
try {
  const undici = require('undici');
  console.log('undici loaded');
  const resp = new undici.Response();
  console.log('response.body', resp.body);
  console.log('body.tee', typeof resp.body.tee);
} catch (e) {
  console.error('Error:', e.message);
  console.error(e.stack);
}