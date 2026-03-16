import { DigitalProduct, Study, DarkPattern, SideEffect, Category } from '../types';
import { products as mockProducts } from '../data';
import { darkPatterns as mockDarkPatterns } from '../data';
import { studies as mockStudies } from '../data';
import { sideEffects as mockSideEffects } from '../data';

const API_BASE_URL = 'http://localhost:3000/api';
const USE_API = true; // Enabled after MongoDB seeding

class DataService {
  private async fetchFromAPI<T>(endpoint: string): Promise<T | null> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.warn(`Failed to fetch from API ${endpoint}:`, error);
      return null;
    }
  }

  async getProducts(category?: string, search?: string): Promise<DigitalProduct[]> {
    if (USE_API) {
      let endpoint = '/products';
      const params = new URLSearchParams();
      if (category) params.append('category', category);
      if (search) params.append('search', search);
      if (params.toString()) endpoint += `?${params.toString()}`;
      
      const data = await this.fetchFromAPI<DigitalProduct[]>(endpoint);
      if (data) return data;
    }
    
    // Fallback to mock data
    let filteredProducts = [...mockProducts];
    if (category) {
      filteredProducts = filteredProducts.filter(p => p.category === category);
    }
    if (search) {
      const searchLower = search.toLowerCase();
      filteredProducts = filteredProducts.filter(p =>
        p.name.toLowerCase().includes(searchLower) ||
        p.description.toLowerCase().includes(searchLower) ||
        p.tags?.some(tag => tag.toLowerCase().includes(searchLower))
      );
    }
    return filteredProducts;
  }

  async getProductById(id: string): Promise<DigitalProduct | null> {
    if (USE_API) {
      const data = await this.fetchFromAPI<DigitalProduct>(`/products/${id}`);
      if (data) return data;
    }
    
    // Fallback to mock data
    const product = mockProducts.find(p => p.id === id);
    return product || null;
  }

  async getDarkPatterns(): Promise<DarkPattern[]> {
    if (USE_API) {
      const data = await this.fetchFromAPI(`/dark-patterns`);
      if (data) return data as DarkPattern[];
    }
    return mockDarkPatterns;
  }

  async getStudies(search?: string): Promise<Study[]> {
    if (USE_API) {
      let endpoint = '/studies';
      if (search) endpoint += `?search=${encodeURIComponent(search)}`;
      const data = await this.fetchFromAPI(endpoint);
      if (data) return data as Study[];
    }
    
    // Fallback to mock data
    let filteredStudies = [...mockStudies];
    if (search) {
      const searchLower = search.toLowerCase();
      filteredStudies = filteredStudies.filter(s =>
        s.title.toLowerCase().includes(searchLower) ||
        s.authors?.some(author => author.toLowerCase().includes(searchLower)) ||
        s.productsAffected?.some(product => product.toLowerCase().includes(searchLower))
      );
    }
    return filteredStudies;
  }

  async getCategories(): Promise<string[]> {
    if (USE_API) {
      const data = await this.fetchFromAPI('/categories');
      if (data) return data as string[];
    }
    
    // Extract unique categories from mock data
    const categories = Array.from(new Set(mockProducts.map(p => p.category)));
    return categories;
  }

  async getSideEffects() {
    if (USE_API) {
      const data = await this.fetchFromAPI('/side-effects');
      if (data) return data;
    }
    return mockSideEffects;
  }
}

export default new DataService();