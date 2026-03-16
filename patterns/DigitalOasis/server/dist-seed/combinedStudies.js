"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.studies = void 0;
const realStudies_1 = require("./realStudies");
const mockStudies_1 = require("./mockStudies");
// Combine real studies (1-11) with generated studies (12-30)
exports.studies = [
    ...realStudies_1.studies,
    ...mockStudies_1.studies,
];
exports.default = exports.studies;
