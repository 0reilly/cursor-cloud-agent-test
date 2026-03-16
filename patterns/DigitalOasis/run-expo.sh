#!/bin/bash
cd /Users/adamoreilly/patterns/DigitalOasis

# Create a preload script that patches Node 16 missing APIs
cat > preload.js << 'EOF'
// Preload script to patch missing APIs in Node 16
console.log('Patching Node 16 compatibility APIs');

// Patch DOMException
if (typeof global.DOMException === 'undefined') {
  global.DOMException = class DOMException extends Error {
    constructor(message, name) {
      super(message);
      this.name = name || 'DOMException';
    }
  };
  console.log('Patched DOMException');
}

// Patch ReadableStream
if (typeof global.ReadableStream === 'undefined') {
  global.ReadableStream = class ReadableStream {
    constructor() {
      // Simple implementation
    }
  };
  console.log('Patched ReadableStream');
}

// Patch os.availableParallelism
const os = require('os');
if (typeof os.availableParallelism !== 'function') {
  os.availableParallelism = function() {
    return Math.max(1, os.cpus().length - 1);
  };
  console.log('Patched os.availableParallelism');
}

// Patch other missing globals
if (typeof global.Blob === 'undefined') {
  global.Blob = class Blob {
    constructor() {
      // Simple implementation
    }
  };
  console.log('Patched Blob');
}

if (typeof global.File === 'undefined') {
  global.File = class File {
    constructor() {
      // Simple implementation
    }
  };
  console.log('Patched File');
}

// Patch AbortSignal.throwIfAborted - missing in Node 16
if (typeof AbortSignal.prototype.throwIfAborted === 'undefined') {
  AbortSignal.prototype.throwIfAborted = function() {
    if (this.aborted) {
      const error = new Error('The operation was aborted');
      error.name = 'AbortError';
      error.code = 'ABORT_ERR';
      throw error;
    }
  };
  console.log('Patched AbortSignal.prototype.throwIfAborted');
}

// Patch missing Array methods for Node 16
if (typeof Array.prototype.toReversed === 'undefined') {
  Array.prototype.toReversed = function() {
    return [...this].reverse();
  };
  console.log('Patched Array.prototype.toReversed');
}

if (typeof Array.prototype.toSorted === 'undefined') {
  Array.prototype.toSorted = function(compareFn) {
    return [...this].sort(compareFn);
  };
  console.log('Patched Array.prototype.toSorted');
}

if (typeof Array.prototype.toSpliced === 'undefined') {
  Array.prototype.toSpliced = function(start, deleteCount, ...items) {
    const newArray = [...this];
    newArray.splice(start, deleteCount, ...items);
    return newArray;
  };
  console.log('Patched Array.prototype.toSpliced');
}

if (typeof Array.prototype.with === 'undefined') {
  Array.prototype.with = function(index, value) {
    const newArray = [...this];
    newArray[index] = value;
    return newArray;
  };
  console.log('Patched Array.prototype.with');
}

// Patch Object.hasOwn - missing in Node 16
if (typeof Object.hasOwn === 'undefined') {
  Object.hasOwn = function(obj, prop) {
    return Object.prototype.hasOwnProperty.call(obj, prop);
  };
  console.log('Patched Object.hasOwn');
}

// Patch URL.canParse - missing in Node 16
if (typeof URL.canParse === 'undefined') {
  URL.canParse = function(url, base) {
    try {
      new URL(url, base);
      return true;
    } catch {
      return false;
    }
  };
  console.log('Patched URL.canParse');
}
EOF

echo "Starting Expo dev server..."
echo "Node version: $(node --version)"
echo ""

# Run expo with our preload script
NODE_OPTIONS="--require ./preload.js --no-warnings" \
EXPO_NO_WATCHMAN=1 \
npx expo start --ios --clear "$@"