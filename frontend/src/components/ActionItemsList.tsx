import { ActionItem } from '@/lib/hooks/useMeetingNotes';

interface ActionItemsListProps {
  items: ActionItem[];
}

export function ActionItemsList({ items }: ActionItemsListProps) {
  if (items.length === 0) {
    return (
      <div className="p-8 text-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <p className="text-gray-600">No action items found in these notes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900">
        Extracted Action Items ({items.length})
      </h3>

      {items.map((item) => (
        <div
          key={item.id}
          className="p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-300 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-base font-medium text-gray-900">
                ✓ {item.description}
              </p>

              <div className="mt-2 flex flex-wrap gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Owner: </span>
                  <span className={item.owner ? 'text-gray-900' : 'text-gray-400 italic'}>
                    {item.owner || 'Unassigned'}
                  </span>
                </div>

                <div>
                  <span className="text-gray-500">Due: </span>
                  <span className={item.due_date ? 'text-gray-900' : 'text-gray-400 italic'}>
                    {item.due_date
                      ? new Date(item.due_date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })
                      : 'No due date'}
                  </span>
                </div>

                {item.confidence !== null && (
                  <div>
                    <span className="text-gray-500">Confidence: </span>
                    <span
                      className={
                        item.confidence >= 0.8
                          ? 'text-green-600 font-medium'
                          : item.confidence >= 0.6
                          ? 'text-yellow-600 font-medium'
                          : 'text-red-600 font-medium'
                      }
                    >
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
