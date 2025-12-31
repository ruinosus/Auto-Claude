/**
 * UserFeedback Component
 *
 * Provides thumbs up/down feedback UI for completed tasks.
 */

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Textarea } from './ui/textarea';
import {
  submitThumbsUp,
  submitThumbsDown,
  isLangfuseWebReady,
} from '../services/langfuse-web';

interface UserFeedbackProps {
  /** Langfuse trace ID for the task */
  traceId: string | null;
  /** Callback when feedback is submitted */
  onFeedbackSubmitted?: (positive: boolean) => void;
  /** Optional className */
  className?: string;
}

export function UserFeedback({ traceId, onFeedbackSubmitted, className = '' }: UserFeedbackProps) {
  const [feedbackState, setFeedbackState] = useState<'none' | 'positive' | 'negative'>('none');
  const [showCommentPopover, setShowCommentPopover] = useState(false);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Don't render if no trace ID or Langfuse not ready
  if (!traceId || !isLangfuseWebReady()) {
    return null;
  }

  const handleThumbsUp = async () => {
    if (feedbackState !== 'none' || isSubmitting) return;

    setIsSubmitting(true);
    const success = await submitThumbsUp(traceId);
    setIsSubmitting(false);

    if (success) {
      setFeedbackState('positive');
      onFeedbackSubmitted?.(true);
    }
  };

  const handleThumbsDown = async () => {
    if (feedbackState !== 'none' || isSubmitting) return;

    // Show comment popover for negative feedback
    setShowCommentPopover(true);
  };

  const handleSubmitNegativeFeedback = async () => {
    setIsSubmitting(true);
    const success = await submitThumbsDown(traceId, comment || undefined);
    setIsSubmitting(false);

    if (success) {
      setFeedbackState('negative');
      setShowCommentPopover(false);
      setComment('');
      onFeedbackSubmitted?.(false);
    }
  };

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <Button
        variant="ghost"
        size="icon"
        className={`h-7 w-7 ${feedbackState === 'positive' ? 'text-green-500' : ''}`}
        onClick={handleThumbsUp}
        disabled={feedbackState !== 'none' || isSubmitting}
        title="Good result"
      >
        <ThumbsUp className="h-4 w-4" />
      </Button>

      <Popover open={showCommentPopover} onOpenChange={setShowCommentPopover}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className={`h-7 w-7 ${feedbackState === 'negative' ? 'text-red-500' : ''}`}
            onClick={handleThumbsDown}
            disabled={feedbackState !== 'none' || isSubmitting}
            title="Needs improvement"
          >
            <ThumbsDown className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              <span className="text-sm font-medium">What went wrong?</span>
            </div>
            <Textarea
              placeholder="Optional: Tell us what could be improved..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="min-h-[80px]"
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowCommentPopover(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSubmitNegativeFeedback} disabled={isSubmitting}>
                Submit
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
