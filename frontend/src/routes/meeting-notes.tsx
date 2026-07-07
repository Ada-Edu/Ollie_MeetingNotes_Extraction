/**
 * Meeting Notes Route - Action Items Extraction
 */

import { createFileRoute } from '@tanstack/react-router';
import MeetingNotesExtraction from '@/pages/MeetingNotesExtraction';

export const Route = createFileRoute('/meeting-notes')({
  component: MeetingNotesPage,
});

function MeetingNotesPage() {
  return <MeetingNotesExtraction />;
}
