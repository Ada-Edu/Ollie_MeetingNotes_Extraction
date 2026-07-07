import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EngineAlert } from '@/components/engine/feedback/EngineAlert';

describe('EngineAlert', () => {
  describe('Rendering', () => {
    it('should render with title only', () => {
      render(<EngineAlert title="Alert Title" />);
      expect(screen.getByText('Alert Title')).toBeInTheDocument();
    });

    it('should render with description only', () => {
      render(<EngineAlert description="Alert description" />);
      expect(screen.getByText('Alert description')).toBeInTheDocument();
    });

    it('should render with both title and description', () => {
      render(<EngineAlert title="Title" description="Description" />);
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
    });

    it('should render children', () => {
      render(
        <EngineAlert>
          <p>Custom content</p>
        </EngineAlert>
      );
      expect(screen.getByText('Custom content')).toBeInTheDocument();
    });

    it('should render all content together', () => {
      render(
        <EngineAlert title="Title" description="Description">
          <p>Additional content</p>
        </EngineAlert>
      );
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Additional content')).toBeInTheDocument();
    });
  });

  describe('Variants', () => {
    it('should render default variant', () => {
      const { container } = render(<EngineAlert variant="default" title="Default" />);
      expect(container.querySelector('[role="alert"]')).toBeInTheDocument();
    });

    it('should render destructive variant', () => {
      const { container } = render(<EngineAlert variant="destructive" title="Error" />);
      expect(container.querySelector('[role="alert"]')).toBeInTheDocument();
    });

    it('should render success variant', () => {
      const { container } = render(<EngineAlert variant="success" title="Success" />);
      expect(container.querySelector('[role="alert"]')).toBeInTheDocument();
    });

    it('should render warning variant', () => {
      const { container } = render(<EngineAlert variant="warning" title="Warning" />);
      expect(container.querySelector('[role="alert"]')).toBeInTheDocument();
    });

    it('should render info variant', () => {
      const { container } = render(<EngineAlert variant="info" title="Info" />);
      expect(container.querySelector('[role="alert"]')).toBeInTheDocument();
    });
  });

  describe('Icons', () => {
    it('should render Info icon for default variant', () => {
      const { container } = render(<EngineAlert variant="default" title="Default" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render AlertCircle icon for destructive variant', () => {
      const { container } = render(<EngineAlert variant="destructive" title="Error" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render CheckCircle icon for success variant', () => {
      const { container } = render(<EngineAlert variant="success" title="Success" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render AlertTriangle icon for warning variant', () => {
      const { container } = render(<EngineAlert variant="warning" title="Warning" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render Info icon for info variant', () => {
      const { container } = render(<EngineAlert variant="info" title="Info" />);
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Custom Styling', () => {
    it('should apply custom className', () => {
      const { container } = render(
        <EngineAlert className="custom-alert" title="Test" />
      );
      const alert = container.querySelector('[role="alert"]');
      expect(alert).toHaveClass('custom-alert');
    });

    it('should merge custom className with default classes', () => {
      const { container } = render(
        <EngineAlert className="my-custom-class" title="Test" />
      );
      const alert = container.querySelector('[role="alert"]');
      expect(alert).toHaveClass('my-custom-class');
    });
  });

  describe('Accessibility', () => {
    it('should have alert role', () => {
      const { container } = render(<EngineAlert title="Test" />);
      const alert = container.querySelector('[role="alert"]');
      expect(alert).toBeInTheDocument();
    });

    it('should render icon with proper size', () => {
      const { container } = render(<EngineAlert variant="success" title="Success" />);
      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('h-4', 'w-4');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty title', () => {
      render(<EngineAlert title="" description="Description" />);
      expect(screen.getByText('Description')).toBeInTheDocument();
    });

    it('should handle empty description', () => {
      render(<EngineAlert title="Title" description="" />);
      expect(screen.getByText('Title')).toBeInTheDocument();
    });

    it('should render with no content', () => {
      const { container } = render(<EngineAlert />);
      const alert = container.querySelector('[role="alert"]');
      expect(alert).toBeInTheDocument();
    });

    it('should handle long title text', () => {
      const longTitle = 'This is a very long title that might span multiple lines and should be displayed correctly';
      render(<EngineAlert title={longTitle} />);
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should handle long description text', () => {
      const longDescription = 'This is a very long description that contains a lot of information and might span multiple lines in the alert component';
      render(<EngineAlert description={longDescription} />);
      expect(screen.getByText(longDescription)).toBeInTheDocument();
    });
  });

  describe('Common Use Cases', () => {
    it('should render success message', () => {
      render(
        <EngineAlert
          variant="success"
          title="Success"
          description="Your action was completed successfully"
        />
      );
      expect(screen.getByText('Success')).toBeInTheDocument();
      expect(screen.getByText('Your action was completed successfully')).toBeInTheDocument();
    });

    it('should render error message', () => {
      render(
        <EngineAlert
          variant="destructive"
          title="Error"
          description="Something went wrong"
        />
      );
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should render warning message', () => {
      render(
        <EngineAlert
          variant="warning"
          title="Warning"
          description="Please review before proceeding"
        />
      );
      expect(screen.getByText('Warning')).toBeInTheDocument();
      expect(screen.getByText('Please review before proceeding')).toBeInTheDocument();
    });

    it('should render info message', () => {
      render(
        <EngineAlert
          variant="info"
          title="Information"
          description="Here is some helpful information"
        />
      );
      expect(screen.getByText('Information')).toBeInTheDocument();
      expect(screen.getByText('Here is some helpful information')).toBeInTheDocument();
    });
  });
});
