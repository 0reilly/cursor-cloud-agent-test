"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.categories = exports.products = exports.studies = exports.sideEffects = exports.darkPatterns = void 0;
var mockDarkPatterns_1 = require("./mockDarkPatterns");
Object.defineProperty(exports, "darkPatterns", { enumerable: true, get: function () { return __importDefault(mockDarkPatterns_1).default; } });
var mockSideEffects_1 = require("./mockSideEffects");
Object.defineProperty(exports, "sideEffects", { enumerable: true, get: function () { return __importDefault(mockSideEffects_1).default; } });
var combinedStudies_1 = require("./combinedStudies");
Object.defineProperty(exports, "studies", { enumerable: true, get: function () { return __importDefault(combinedStudies_1).default; } });
var mockProducts_1 = require("./mockProducts");
Object.defineProperty(exports, "products", { enumerable: true, get: function () { return __importDefault(mockProducts_1).default; } });
var mockCategories_1 = require("./mockCategories");
Object.defineProperty(exports, "categories", { enumerable: true, get: function () { return __importDefault(mockCategories_1).default; } });
