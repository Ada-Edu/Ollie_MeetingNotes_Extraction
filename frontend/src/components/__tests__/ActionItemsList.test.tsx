import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ActionItemsList } from '../ActionItemsList';
import { ActionItem } from '@/lib/hooks/useMeetingNotes';

describe('ActionItemsList', () => {
  const mockActionItems: ActionItem[] = [
    {
      id: '1',
      description: 'Follow up with Sarah about project timeline',
      owner: 'John',
      due_date: '2026-07-15',
      confidence: 0.95,
      created_at: '2026-07-07T10:00:00Z'
    },
    {
      id: '2',
      description: 'Review design document',
      owner: 'Mike',
      due_date: '2026-07-10',
      confidence: 0.87,
      created_at: '2026-07-07T10:00:00Z'
    },
    {
      id: '3',
      description: 'Update documentation',
      owner: null,
      due_date: null,
      confidence: 0.45,
      created_at: '2026-07-07T10:00:00Z'
    }
  ];

  describe('Empty state', () => {
    it('should display empty state message when no items', () => {
      render(<ActionItemsList items={[]} />);

      expect(screen.getByText('No action items found in these notes.')).toBeInTheDocument();
    });

    it('should apply correct styling to empty state', () => {
      const { container } = render(<ActionItemsList items={[]} />);

      const emptyState = container.querySelector('.p-8');
      expect(emptyState).toHaveClass('text-center', 'bg-gray-50', 'rounded-lg');
    });
  });

  describe('With action items', () => {
    it('should render all action items', () => {
      render(<ActionItemsList items={mockActionItems} />);

      expect(screen.getByText(/Follow up with Sarah about project timeline/)).toBeInTheDocument();
      expect(screen.getByText(/Review design document/)).toBeInTheDocument();
      expect(screen.getByText(/Update documentation/)).toBeInTheDocument();
    });

    it('should display item count in header', () => {
      render(<ActionItemsList items={mockActionItems} />);

      expect(screen.getByText(`Extracted Action Items (${mockActionItems.length})`)).toBeInTheDocument();
    });

    it('should display owner information correctly', () => {
      render(<ActionItemsList items={mockActionItems} />);

      expect(screen.getByText('John')).toBeInTheDocument();
      expect(screen.getByText('Mike')).toBeInTheDocument();
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });

    it('should format due dates correctly', () => {
      render(<ActionItemsList items={mockActionItems} />);

      expect(screen.getByText('Jul 15, 2026')).toBeInTheDocument();
      expect(screen.getByText('Jul 10, 2026')).toBeInTheDocument();
      expect(screen.getByText('No due date')).toBeInTheDocument();
    });

    it('should display confidence percentages', () => {
      render(<ActionItemsList items={mockActionItems} />);

      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('87%')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('should apply correct confidence color classes', () => {
      render(<ActionItemsList items={mockActionItems} />);

      const highConfidence = screen.getByText('95%');
      expect(highConfidence).toHaveClass('text-green-600', 'font-medium');

      const mediumConfidence = screen.getByText('87%');
      expect(mediumConfidence).toHaveClass('text-green-600', 'font-medium');

      const lowConfidence = screen.getByText('45%');
      expect(lowConfidence).toHaveClass('text-red-600', 'font-medium');
    });

    it('should render checkmark prefix for each item', () => {
      const { container } = render(<ActionItemsList items={mockActionItems} />);

      const descriptions = container.querySelectorAll('p.text-base.font-medium');
      descriptions.forEach((desc) => {
        expect(desc.textContent).toMatch(/^✓/);
      });
    });

    it('should handle items with null confidence', () => {
      const itemsWithNullConfidence: ActionItem[] = [
        {
          id: '1',
          description: 'Test item',
          owner: 'John',
          due_date: '2026-07-15',
          confidence: null,
          created_at: '2026-07-07T10:00:00Z'
        }
      ];

      render(<ActionItemsList items={itemsWithNullConfidence} />);

      expect(screen.getByText(/Test item/)).toBeInTheDocument();
      expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument();
    });

    it('should apply hover effects to action items', () => {
      const { container } = render(<ActionItemsList items={mockActionItems} />);

      const items = container.querySelectorAll('.p-4.bg-white');
      items.forEach((item) => {
        expect(item).toHaveClass('hover:border-blue-300', 'transition-colors');
      });
    });
  });

  describe('Edge cases', () => {
    it('should handle single action item', () => {
      const singleItem = [mockActionItems[0]];
      render(<ActionItemsList items={singleItem} />);

      expect(screen.getByText('Extracted Action Items (1)')).toBeInTheDocument();
      expect(screen.getByText(/Follow up with Sarah/)).toBeInTheDocument();
    });

    it('should handle items with very long descriptions', () => {
      const longDescItem: ActionItem[] = [
        {
          id: '1',
          description: 'This is a very long action item description that should still render properly without breaking the layout or causing any visual issues in the component',
          owner: 'John',
          due_date: '2026-07-15',
          confidence: 0.95,
          created_at: '2026-07-07T10:00:00Z'
        }
      ];

      const { container } = render(<ActionItemsList items={longDescItem} />);

      expect(screen.getByText(/This is a very long action item/)).toBeInTheDocument();
      expect(container.querySelector('.flex-1')).toBeInTheDocument();
    });

    it('should handle yellow confidence range (0.6-0.8)', () => {
      const yellowConfidenceItem: ActionItem[] = [
        {
          id: '1',
          description: 'Medium confidence item',
          owner: 'Jane',
          due_date: '2026-07-15',
          confidence: 0.7,
          created_at: '2026-07-07T10:00:00Z'
        }
      ];

      render(<ActionItemsList items={yellowConfidenceItem} />);

      const confidenceElement = screen.getByText('70%');
      expect(confidenceElement).toHaveClass('text-yellow-600', 'font-medium');
    });
  });
});
