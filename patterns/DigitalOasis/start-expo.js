// Patch ReadableStream for Node 16 compatibility
if (typeof global.ReadableStream === 'undefined') {
  try {
    // Try to use stream/web polyfill if available
    const { ReadableStream } = require('stream/web');
    global.ReadableStream = ReadableStream;
    console.log('Patched ReadableStream using stream/web');
  } catch (err) {
    // Fallback to basic implementation
    console.log('Could not patch ReadableStream, using minimal implementation');
    global.ReadableStream = class ReadableStream {
      constructor() {
        console.warn('ReadableStream polyfill called');
      }
    };
  }
}

// Now run Expo CLI
require('expo/node_modules/@expo/cli/build/bin/cli');