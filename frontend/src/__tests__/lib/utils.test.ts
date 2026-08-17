import { describe, it, expect } from 'vitest';
import { cn } from '@/lib/utils';

describe('cn utility', () => {
  describe('Basic Functionality', () => {
    it('should merge single class', () => {
      expect(cn('text-red-500')).toBe('text-red-500');
    });

    it('should merge multiple classes', () => {
      const result = cn('text-red-500', 'bg-blue-500');
      expect(result).toContain('text-red-500');
      expect(result).toContain('bg-blue-500');
    });

    it('should handle empty input', () => {
      expect(cn()).toBe('');
    });

    it('should handle undefined values', () => {
      expect(cn('text-red-500', undefined, 'bg-blue-500')).toContain('text-red-500');
    });

    it('should handle null values', () => {
      expect(cn('text-red-500', null, 'bg-blue-500')).toContain('text-red-500');
    });

    it('should handle false values', () => {
      expect(cn('text-red-500', false, 'bg-blue-500')).toContain('text-red-500');
    });
  });

  describe('Conditional Classes', () => {
    it('should include class when condition is true', () => {
      const isActive = true;
      expect(cn('base-class', isActive && 'active-class')).toContain('active-class');
    });

    it('should exclude class when condition is false', () => {
      const isActive = false;
      expect(cn('base-class', isActive && 'active-class')).not.toContain('active-class');
    });

    it('should handle multiple conditional classes', () => {
      const isActive = true;
      const isDisabled = false;
      const result = cn(
        'base-class',
        isActive && 'active-class',
        isDisabled && 'disabled-class'
      );
      expect(result).toContain('active-class');
      expect(result).not.toContain('disabled-class');
    });
  });

  describe('Tailwind Merge', () => {
    it('should merge conflicting padding classes', () => {
      const result = cn('p-4', 'p-8');
      expect(result).toBe('p-8');
      expect(result).not.toContain('p-4');
    });

    it('should merge conflicting margin classes', () => {
      const result = cn('m-2', 'm-4');
      expect(result).toBe('m-4');
    });

    it('should merge conflicting text color classes', () => {
      const result = cn('text-red-500', 'text-blue-500');
      expect(result).toBe('text-blue-500');
    });

    it('should merge conflicting background classes', () => {
      const result = cn('bg-red-500', 'bg-blue-500');
      expect(result).toBe('bg-blue-500');
    });

    it('should keep non-conflicting classes', () => {
      const result = cn('p-4', 'text-red-500');
      expect(result).toContain('p-4');
      expect(result).toContain('text-red-500');
    });

    it('should handle directional padding overrides', () => {
      const result = cn('p-4', 'px-8');
      // tailwind-merge keeps both when specificity differs
      expect(result).toBe('p-4 px-8');
    });

    it('should handle specific directional overrides', () => {
      const result = cn('p-4', 'pt-8');
      // tailwind-merge keeps both when specificity differs
      expect(result).toBe('p-4 pt-8');
    });
  });

  describe('Array Inputs', () => {
    it('should handle array of classes', () => {
      const classes = ['text-red-500', 'bg-blue-500'];
      const result = cn(classes);
      expect(result).toContain('text-red-500');
      expect(result).toContain('bg-blue-500');
    });

    it('should handle nested arrays', () => {
      const result = cn(['text-red-500', ['bg-blue-500', 'p-4']]);
      expect(result).toContain('text-red-500');
      expect(result).toContain('bg-blue-500');
      expect(result).toContain('p-4');
    });
  });

  describe('Object Inputs', () => {
    it('should include classes with truthy values', () => {
      const result = cn({
        'text-red-500': true,
        'bg-blue-500': true
      });
      expect(result).toContain('text-red-500');
      expect(result).toContain('bg-blue-500');
    });

    it('should exclude classes with falsy values', () => {
      const result = cn({
        'text-red-500': true,
        'bg-blue-500': false
      });
      expect(result).toContain('text-red-500');
      expect(result).not.toContain('bg-blue-500');
    });
  });

  describe('Complex Scenarios', () => {
    it('should handle mix of strings, conditionals, and objects', () => {
      const isActive = true;
      const isDisabled = false;
      const result = cn(
        'base-class',
        isActive && 'active-class',
        {
          'disabled-class': isDisabled,
          'enabled-class': !isDisabled
        },
        'extra-class'
      );
      expect(result).toContain('base-class');
      expect(result).toContain('active-class');
      expect(result).toContain('enabled-class');
      expect(result).toContain('extra-class');
      expect(result).not.toContain('disabled-class');
    });

    it('should handle variant-based styling', () => {
      const variant = 'primary';
      const result = cn(
        'base-button',
        variant === 'primary' && 'bg-blue-500 text-white',
        variant === 'secondary' && 'bg-gray-500 text-white'
      );
      expect(result).toContain('base-button');
      expect(result).toContain('bg-blue-500');
      expect(result).toContain('text-white');
    });

    it('should merge overlapping variant classes', () => {
      const variant = 'primary';
      const size = 'large';
      const result = cn(
        'p-4',
        variant === 'primary' && 'p-6 bg-blue-500',
        size === 'large' && 'text-lg'
      );
      expect(result).toBe('p-6 bg-blue-500 text-lg');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty strings', () => {
      expect(cn('', 'text-red-500')).toBe('text-red-500');
    });

    it('should handle whitespace', () => {
      expect(cn('  text-red-500  ', '  bg-blue-500  ')).toContain('text-red-500');
    });

    it('should deduplicate identical classes', () => {
      const result = cn('text-red-500', 'text-red-500');
      expect(result).toBe('text-red-500');
    });

    it('should handle very long class lists', () => {
      const classes = Array.from({ length: 50 }, (_, i) => `class-${i}`);
      const result = cn(...classes);
      expect(result).toContain('class-0');
      expect(result).toContain('class-49');
    });
  });
});
