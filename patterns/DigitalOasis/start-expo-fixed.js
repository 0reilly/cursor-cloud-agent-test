#!/usr/bin/env node

// Monkey patch for Node 16 compatibility
const originalModuleLoad = Module._load;
Module._load = function(request, parent, isMain) {
  // Intercept require for undici
  if (request.includes('undici/lib/web/fetch')) {
    const module = originalModuleLoad.call(this, request, parent, isMain);
    
    // Patch ReadableStream if missing
    if (typeof global.ReadableStream === 'undefined') {
      try {
        // Minimal ReadableStream implementation
        global.ReadableStream = class ReadableStream {
          constructor() {
            // Simple implementation
          }
        };
        console.log('Patched global.ReadableStream');
      } catch (err) {
        console.log('Failed to patch ReadableStream:', err.message);
      }
    }
    
    return module;
  }
  
  return originalModuleLoad.call(this, request, parent, isMain);
};

// Patch os.availableParallelism for Node < 19
const os = require('os');
if (typeof os.availableParallelism !== 'function') {
  os.availableParallelism = function() {
    return Math.max(1, os.cpus().length - 1);
  };
  console.log('Patched os.availableParallelism');
}

// Now require the actual expo CLI
require('expo/bin/cli');