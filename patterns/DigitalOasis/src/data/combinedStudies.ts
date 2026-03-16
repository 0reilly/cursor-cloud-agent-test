// @ts-nocheck
import { Study } from '../types';
import { studies as realStudies } from './realStudies';
import { studies as mockStudies } from './mockStudies';

// Combine real studies (1-11) with generated studies (12-30)
export const studies: Study[] = [
  ...realStudies,
  ...mockStudies,
];

export default studies;