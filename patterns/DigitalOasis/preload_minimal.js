// Minimal polyfills for Node 18
console.log('Loading minimal polyfills');

// Patch missing Array methods for Node 18
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

// Patch ReadableStream using Node's built-in if available
if (typeof global.ReadableStream === 'undefined') {
  try {
    const { ReadableStream } = require('stream/web');
    global.ReadableStream = ReadableStream;
    console.log('Patched ReadableStream with Node built-in');
  } catch (err) {
    console.warn('Failed to load stream/web:', err.message);
    // Dummy implementation as fallback
    global.ReadableStream = class ReadableStream {
      constructor() {}
    };
    console.log('Patched ReadableStream with dummy class');
  }
}

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

// Patch Object.hasOwn
if (typeof Object.hasOwn === 'undefined') {
  Object.hasOwn = function(obj, prop) {
    return Object.prototype.hasOwnProperty.call(obj, prop);
  };
  console.log('Patched Object.hasOwn');
}

console.log('Minimal polyfills loaded');