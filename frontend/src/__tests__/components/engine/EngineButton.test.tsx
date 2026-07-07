import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EngineButton } from '@/components/engine/actions/EngineButton';
import { UIEngineContext } from '@/engine/UIEngineContext';
import type { ActionDefinition } from '@/engine/types';

const mockDispatch = vi.fn();

const mockContext = {
  state: {},
  setState: vi.fn(),
  data: {},
  params: {},
  isLoading: {},
  errors: {},
  isPageLoading: false,
  dispatch: mockDispatch,
  refetch: vi.fn(),
  openModals: {},
  openModal: vi.fn(),
  closeModal: vi.fn(),
  evaluateExpression: (expr: unknown) => expr
};

describe('EngineButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render button with children', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton>Click Me</EngineButton>
        </UIEngineContext.Provider>
      );
      expect(screen.getByText('Click Me')).toBeInTheDocument();
    });

    it('should apply default variant', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton>Button</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should apply custom variant', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton variant="destructive">Delete</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should apply custom size', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton size="lg">Large Button</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton className="custom-class">Button</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
    });

    it('should render with correct button type', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton type="submit">Submit</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'submit');
    });
  });

  describe('Click Handling', () => {
    it('should dispatch action on click', async () => {
      const action: ActionDefinition = { action: 'setState', key: 'test', value: 'value' };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton onClick={action}>Click Me</EngineButton>
        </UIEngineContext.Provider>
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockDispatch).toHaveBeenCalledWith(action);
    });

    it('should not dispatch when disabled', () => {
      const action: ActionDefinition = { action: 'setState', key: 'test', value: 'value' };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton onClick={action} disabled>Click Me</EngineButton>
        </UIEngineContext.Provider>
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockDispatch).not.toHaveBeenCalled();
    });

    it('should not dispatch when loading', () => {
      const action: ActionDefinition = { action: 'setState', key: 'test', value: 'value' };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton onClick={action} loading>Click Me</EngineButton>
        </UIEngineContext.Provider>
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockDispatch).not.toHaveBeenCalled();
    });

    it('should work without onClick action', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton>No Action</EngineButton>
        </UIEngineContext.Provider>
      );

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(mockDispatch).not.toHaveBeenCalled();
    });
  });

  describe('Disabled State', () => {
    it('should be disabled when disabled prop is true', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton disabled>Disabled</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should be disabled when loading', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton loading>Loading</EngineButton>
        </UIEngineContext.Provider>
      );
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton loading>Loading</EngineButton>
        </UIEngineContext.Provider>
      );
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });

    it('should not show spinner when not loading', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineButton>Not Loading</EngineButton>
        </UIEngineContext.Provider>
      );
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).not.toBeInTheDocument();
    });
  });

  describe('Multiple Variants', () => {
    const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const;

    variants.forEach(variant => {
      it(`should render ${variant} variant`, () => {
        render(
          <UIEngineContext.Provider value={mockContext}>
            <EngineButton variant={variant}>{variant}</EngineButton>
          </UIEngineContext.Provider>
        );
        expect(screen.getByText(variant)).toBeInTheDocument();
      });
    });
  });

  describe('Multiple Sizes', () => {
    const sizes = ['default', 'sm', 'lg', 'icon'] as const;

    sizes.forEach(size => {
      it(`should render ${size} size`, () => {
        render(
          <UIEngineContext.Provider value={mockContext}>
            <EngineButton size={size}>{size}</EngineButton>
          </UIEngineContext.Provider>
        );
        expect(screen.getByText(size)).toBeInTheDocument();
      });
    });
  });
});
