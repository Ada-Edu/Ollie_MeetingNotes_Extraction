import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MeetingNotesExtraction } from '../pages/MeetingNotesExtraction';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock hooks
vi.mock('../lib/hooks/useMeetingNotes', () => ({
  useCreateMeetingNote: () => ({
    mutateAsync: vi.fn(),
    isPending: false
  }),
  useExtractionRun: () => ({
    data: null,
    isLoading: false
  })
}));

describe('MeetingNotesExtraction', () => {
  const queryClient = new QueryClient();

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MeetingNotesExtraction />
      </QueryClientProvider>
    );
  };

  it('renders the page title', () => {
    renderComponent();
    expect(screen.getByText(/Meeting Notes → Action Items/i)).toBeInTheDocument();
  });

  it('renders textarea for notes input', () => {
    renderComponent();
    const textarea = screen.getByPlaceholderText(/Paste your meeting notes/i);
    expect(textarea).toBeInTheDocument();
  });

  it('renders submit button', () => {
    renderComponent();
    const button = screen.getByRole('button', { name: /Extract Action Items/i });
    expect(button).toBeInTheDocument();
  });

  it('disables submit button when notes are empty', () => {
    renderComponent();
    const button = screen.getByRole('button', { name: /Extract Action Items/i });
    expect(button).toBeDisabled();
  });

  it('shows character count', () => {
    renderComponent();
    expect(screen.getByText(/0 \/ 10,000 characters/i)).toBeInTheDocument();
  });

  it('updates character count when typing', () => {
    renderComponent();
    const textarea = screen.getByPlaceholderText(/Paste your meeting notes/i);

    fireEvent.change(textarea, { target: { value: 'Test notes' } });

    expect(screen.getByText(/10 \/ 10,000 characters/i)).toBeInTheDocument();
  });

  it('renders tips section', () => {
    renderComponent();
    expect(screen.getByText(/Tips for best results:/i)).toBeInTheDocument();
  });
});
