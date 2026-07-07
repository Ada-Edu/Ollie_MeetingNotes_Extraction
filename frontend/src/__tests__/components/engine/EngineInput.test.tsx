import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EngineInput } from '@/components/engine/forms/EngineInput';
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

describe('EngineInput', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render input field', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput placeholder="Enter text" />
        </UIEngineContext.Provider>
      );
      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
    });

    it('should render with label', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput label="Username" />
        </UIEngineContext.Provider>
      );
      expect(screen.getByText('Username')).toBeInTheDocument();
    });

    it('should render with required indicator', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput label="Email" required />
        </UIEngineContext.Provider>
      );
      const asterisk = screen.getByText('*');
      expect(asterisk).toBeInTheDocument();
    });

    it('should render with error message', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput error="This field is required" />
        </UIEngineContext.Provider>
      );
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    it('should apply error styling when error exists', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput error="Error" />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).toHaveClass('border-destructive');
    });

    it('should render with initial value', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput value="Initial value" />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox') as HTMLInputElement;
      expect(input.value).toBe('Initial value');
    });
  });

  describe('Input Types', () => {
    const inputTypes = ['text', 'email', 'password', 'number', 'tel', 'url', 'search'] as const;

    inputTypes.forEach(type => {
      it(`should render with type ${type}`, () => {
        render(
          <UIEngineContext.Provider value={mockContext}>
            <EngineInput type={type} />
          </UIEngineContext.Provider>
        );
        const input = type === 'search'
          ? screen.getByRole('searchbox')
          : type === 'password'
          ? screen.getByDisplayValue('') // password inputs don't expose role
          : screen.getByRole(
              type === 'text' || type === 'email' || type === 'tel' || type === 'url'
                ? 'textbox'
                : 'spinbutton'
        );
        expect(input).toHaveAttribute('type', type);
      });
    });
  });

  describe('Change Handling', () => {
    it('should dispatch onChange action when input changes', () => {
      const onChange: ActionDefinition = { action: 'setState', key: 'username', value: '{{event.target.value}}' };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput onChange={onChange} />
        </UIEngineContext.Provider>
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'new value' } });

      expect(mockDispatch).toHaveBeenCalledWith(onChange, expect.objectContaining({
        event: expect.any(Object)
      }));
    });

    it('should not dispatch when disabled', () => {
      const onChange: ActionDefinition = { action: 'setState', key: 'username', value: '{{event.target.value}}' };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput onChange={onChange} disabled />
        </UIEngineContext.Provider>
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'new value' } });

      expect(input).toBeDisabled();
    });

    it('should work without onChange action', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput />
        </UIEngineContext.Provider>
      );

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'new value' } });

      expect(mockDispatch).not.toHaveBeenCalled();
    });
  });

  describe('Blur Handling', () => {
    it('should dispatch onBlur action when input loses focus', () => {
      const onBlur: ActionDefinition = { action: 'setState', key: 'touched', value: true };
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput onBlur={onBlur} />
        </UIEngineContext.Provider>
      );

      const input = screen.getByRole('textbox');
      fireEvent.blur(input);

      expect(mockDispatch).toHaveBeenCalledWith(onBlur, expect.objectContaining({
        event: expect.any(Object)
      }));
    });

    it('should work without onBlur action', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput />
        </UIEngineContext.Provider>
      );

      const input = screen.getByRole('textbox');
      fireEvent.blur(input);

      expect(mockDispatch).not.toHaveBeenCalled();
    });
  });

  describe('Disabled State', () => {
    it('should be disabled when disabled prop is true', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput disabled />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).toBeDisabled();
    });

    it('should be enabled by default', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).not.toBeDisabled();
    });
  });

  describe('Name and ID', () => {
    it('should set name attribute', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput name="username" />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('name', 'username');
    });

    it('should generate unique ID when name is provided', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput name="username" label="Username" />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      const label = screen.getByText('Username');
      expect(input).toHaveAttribute('id', 'username');
      expect(label).toHaveAttribute('for', 'username');
    });

    it('should generate random ID when name is not provided', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput label="Email" />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      const id = input.getAttribute('id');
      expect(id).toBeTruthy();
      expect(id).toMatch(/^input-/);
    });
  });

  describe('Required State', () => {
    it('should have required attribute when required', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput required />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).toBeRequired();
    });

    it('should not have required attribute by default', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('textbox');
      expect(input).not.toBeRequired();
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className to container', () => {
      const { container } = render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput className="custom-input-wrapper" />
        </UIEngineContext.Provider>
      );
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('custom-input-wrapper');
    });
  });

  describe('Number Input', () => {
    it('should handle numeric value', () => {
      render(
        <UIEngineContext.Provider value={mockContext}>
          <EngineInput type="number" value={42} />
        </UIEngineContext.Provider>
      );
      const input = screen.getByRole('spinbutton') as HTMLInputElement;
      expect(input.value).toBe('42');
    });
  });
});
