import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ActionItemsList } from '@/components/ActionItemsList';
import { ActionItem } from '@/lib/hooks/useMeetingNotes';

describe('ActionItemsList', () => {
  describe('Empty State', () => {
    it('should display empty state when no items provided', () => {
      render(<ActionItemsList items={[]} />);
      expect(screen.getByText(/no action items found/i)).toBeInTheDocument();
    });

    it('should render empty state with proper styling', () => {
      const { container } = render(<ActionItemsList items={[]} />);
      const emptyDiv = container.querySelector('.border-dashed');
      expect(emptyDiv).toBeInTheDocument();
    });
  });

  describe('Items Display', () => {
    const mockItems: ActionItem[] = [
      {
        id: '1',
        description: 'Follow up with Sarah',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.95,
        created_at: '2026-07-07T10:00:00Z'
      },
      {
        id: '2',
        description: 'Review design document',
        owner: null,
        due_date: null,
        confidence: null,
        created_at: '2026-07-07T11:00:00Z'
      }
    ];

    it('should display count of action items', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText(/extracted action items \(2\)/i)).toBeInTheDocument();
    });

    it('should render all action items', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText(/Follow up with Sarah/)).toBeInTheDocument();
      expect(screen.getByText(/Review design document/)).toBeInTheDocument();
    });

    it('should display owner when provided', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText('John')).toBeInTheDocument();
    });

    it('should display "Unassigned" when owner is null', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });

    it('should format due date correctly', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText(/jul 15, 2026/i)).toBeInTheDocument();
    });

    it('should display "No due date" when due date is null', () => {
      render(<ActionItemsList items={mockItems} />);
      expect(screen.getByText('No due date')).toBeInTheDocument();
    });
  });

  describe('Confidence Display', () => {
    it('should display confidence percentage when provided', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Test task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.85,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should apply green color for high confidence (>= 0.8)', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Test task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.9,
        created_at: '2026-07-07T10:00:00Z'
      }];
      const { container } = render(<ActionItemsList items={items} />);
      const confidenceSpan = screen.getByText('90%');
      expect(confidenceSpan).toHaveClass('text-green-600');
    });

    it('should apply yellow color for medium confidence (0.6-0.79)', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Test task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.7,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      const confidenceSpan = screen.getByText('70%');
      expect(confidenceSpan).toHaveClass('text-yellow-600');
    });

    it('should apply red color for low confidence (< 0.6)', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Test task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.5,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      const confidenceSpan = screen.getByText('50%');
      expect(confidenceSpan).toHaveClass('text-red-600');
    });

    it('should not display confidence when null', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Test task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: null,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.queryByText(/confidence:/i)).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle single item', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Single task',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.9,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.getByText(/extracted action items \(1\)/i)).toBeInTheDocument();
    });

    it('should handle long description text', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'This is a very long description that might wrap to multiple lines and should still be displayed correctly',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.9,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.getByText(/this is a very long description/i)).toBeInTheDocument();
    });

    it('should handle items with all null optional fields', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Minimal task',
        owner: null,
        due_date: null,
        confidence: null,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.getByText(/Minimal task/)).toBeInTheDocument();
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
      expect(screen.getByText('No due date')).toBeInTheDocument();
    });

    it('should render checkmark icon for each item', () => {
      const items: ActionItem[] = [{
        id: '1',
        description: 'Task with checkmark',
        owner: 'John',
        due_date: '2026-07-15',
        confidence: 0.9,
        created_at: '2026-07-07T10:00:00Z'
      }];
      render(<ActionItemsList items={items} />);
      expect(screen.getByText(/✓ task with checkmark/i)).toBeInTheDocument();
    });
  });
});
