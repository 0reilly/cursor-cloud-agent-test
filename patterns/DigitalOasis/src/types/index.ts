export type DarkPatternType =
  | 'misleading'
  | 'sneaking'
  | 'urgent'
  | 'scarcity'
  | 'social_proof'
  | 'obstruction'
  | 'forced_action'
  | 'confirmshaming';

export interface DarkPattern {
  id: string;
  type: DarkPatternType;
  name: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  example: string;
}

export interface SideEffect {
  id: string;
  name: string;
  description: string;
  category: 'mental_health' | 'privacy' | 'financial' | 'addiction' | 'productivity';
  severity: 'low' | 'medium' | 'high';
}

export interface Study {
  id: string;
  title: string;
  summary: string;
  authors: string[];
  publication: string;
  year: number;
  url?: string;
  findings: string[];
  productsAffected: string[];
}

export interface DigitalProduct {
  id: string;
  name: string;
  category: 'social_media' | 'ecommerce' | 'productivity' | 'gaming' | 'streaming' | 'dating' | 'finance';
  description: string;
  darkPatterns: {
    pattern: DarkPattern;
    prevalence: 'rare' | 'common' | 'ubiquitous';
    description: string;
    verification?: string;
  }[];
  sideEffects: SideEffect[];
  transparencyScore: number; // 0-100 (higher is better)
  icon: string; // emoji or image url
  studies: Study[];
  tags: string[];
}

export interface Category {
  id: string;
  name: string;
  description: string;
  icon: string;
  productCount: number;
}
