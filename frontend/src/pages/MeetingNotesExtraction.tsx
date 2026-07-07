import { useState } from 'react';
import { useCreateMeetingNote, useExtractionRun } from '@/lib/hooks/useMeetingNotes';
import { ActionItemsList } from '@/components/ActionItemsList';

export function MeetingNotesExtraction() {
  const [notes, setNotes] = useState('');
  const [extractionRunId, setExtractionRunId] = useState<string | null>(null);

  const createNote = useCreateMeetingNote();
  const { data: extractionRun, isLoading: isLoadingRun } = useExtractionRun(extractionRunId);

  const handleSubmit = async () => {
    if (!notes.trim()) return;

    try {
      const result = await createNote.mutateAsync(notes);
      setExtractionRunId(result.extraction_run_id);
    } catch (error) {
      console.error('Failed to create extraction:', error);
    }
  };

  const handleReset = () => {
    setNotes('');
    setExtractionRunId(null);
  };

  const isProcessing = extractionRun?.status === 'processing' || isLoadingRun;
  const isCompleted = extractionRun?.status === 'completed';
  const isFailed = extractionRun?.status === 'failed';

  return (
    <div className="container mx-auto p-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Meeting Notes → Action Items
        </h1>
        <p className="text-gray-600">
          Paste your meeting notes below and AI will extract actionable tasks with owners and due dates.
        </p>
      </div>

      {/* Input Section */}
      <div className="mb-8 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Meeting Notes:
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Paste your meeting notes here...

Example:
- John needs to follow up with Sarah about Q4 budget by next Friday
- Review architectural design doc
- Schedule team sync for next week"
          className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          maxLength={10000}
          disabled={isProcessing}
        />
        <div className="mt-2 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {notes.length} / 10,000 characters
          </p>
          <div className="flex gap-2">
            {extractionRunId && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                New Extraction
              </button>
            )}
            <button
              onClick={handleSubmit}
              disabled={!notes.trim() || createNote.isPending || isProcessing}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {createNote.isPending || isProcessing
                ? 'Processing...'
                : 'Extract Action Items'}
            </button>
          </div>
        </div>
      </div>

      {/* Status and Results Section */}
      {extractionRunId && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          {/* Status Indicator */}
          {isProcessing && (
            <div className="mb-6 flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <div>
                <p className="font-medium text-blue-900">Processing...</p>
                <p className="text-sm text-blue-700">
                  AI is analyzing your notes and extracting action items.
                </p>
              </div>
            </div>
          )}

          {isCompleted && extractionRun && (
            <>
              <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="font-medium text-green-900">✓ Extraction Complete</p>
                {extractionRun.model_provider && (
                  <p className="text-sm text-green-700 mt-1">
                    Model: {extractionRun.model_provider}/{extractionRun.model_name}
                  </p>
                )}
              </div>

              <ActionItemsList items={extractionRun.action_items || []} />
            </>
          )}

          {isFailed && extractionRun && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="font-medium text-red-900">✗ Extraction Failed</p>
              <p className="text-sm text-red-700 mt-2">
                {extractionRun.error_message || 'An unknown error occurred'}
              </p>
              <p className="text-sm text-red-600 mt-3">
                Please try again or contact support if the issue persists.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      {!extractionRunId && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <h3 className="font-medium text-gray-900 mb-2">Tips for best results:</h3>
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li>Include clear action items with verbs (review, schedule, follow up, etc.)</li>
            <li>Mention owner names when available</li>
            <li>Specify due dates when mentioned (e.g., "by Friday", "next week")</li>
            <li>The AI won't hallucinate - unclear owners/dates will show as "Unassigned"/"No due date"</li>
          </ul>
        </div>
      )}
    </div>
  );
}

export default MeetingNotesExtraction;
