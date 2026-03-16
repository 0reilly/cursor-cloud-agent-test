// Polyfill ReadableStream for Node 16
if (typeof global.ReadableStream === 'undefined') {
  const { Readable } = require('stream');
  // Minimal polyfill - just enough for undici
  global.ReadableStream = class ReadableStream {
    constructor(underlyingSource = {}) {
      this._readable = new Readable({
        read(size) {
          if (underlyingSource.start) {
            const controller = {
              enqueue(chunk) {
                this._readable.push(chunk);
              },
              close() {
                this._readable.push(null);
              },
              error(err) {
                this._readable.destroy(err);
              }
            };
            underlyingSource.start(controller);
          }
        }
      });
    }
    // Minimal implementation
    getReader() {
      return {
        read() {
          return new Promise((resolve, reject) => {
            const chunk = this._readable.read();
            if (chunk) {
              resolve({ value: chunk, done: false });
            } else {
              resolve({ done: true });
            }
          });
        }
      };
    }
  };
}